#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "jinja2>=3.1.6",
#     "watchdog>=6.0.0",
#     "weasyprint>=68.0",
# ]
# ///

"""
Wee - High-performance Jinja2 template to PDF renderer with hot-reload

A fast CLI tool for rendering Jinja2 templates to PDF with instant hot-reload
when templates or context files change.

Features:
- Near-instant hot-reloads with optimized file watching
- Template environment folder support for template extending
- External context.json file monitoring
- High-performance caching and debouncing
- Professional CLI interface with help system
"""

import os
import sys
import time
import json
import signal
import platform
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from weasyprint import HTML, CSS
except ImportError as e:
    print(f"Error: Missing required package - {e}")
    print("\nThis is a PEP 723 script with inline dependencies.")
    print("Install dependencies with one of these methods:")
    print("\n  Option 1 - Using pip:")
    print("    pip install jinja2 weasyprint watchdog")
    print("\n  Option 2 - Using uv (recommended):")
    print("    uv run wee.py")
    print("\n  Option 3 - Using pipx:")
    print("    pipx run wee.py")
    sys.exit(1)

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class WeeConfig:
    """Configuration container for Wee."""
    
    def __init__(self):
        self.template_file: Optional[str] = None
        self.template_dir: Optional[str] = None
        self.output_pdf: str = "output.pdf"
        self.context_file: Optional[str] = None
        self.context_data: Dict[str, Any] = {}
        self.watch_mode: bool = False
        self.auto_open: bool = True
        self.debounce_ms: int = 100  # Faster debounce for instant reloads


class TemplateRenderer:
    """High-performance Jinja2 template renderer with caching."""
    
    def __init__(self, config: WeeConfig):
        self.config = config
        self._env_cache: Optional[Environment] = None
        self._template_cache: Dict[str, Any] = {}
        
    def _get_environment(self) -> Environment:
        """Get or create cached Jinja2 environment."""
        if self._env_cache is None:
            template_dirs = []
            
            # Add template directory if specified
            if self.config.template_dir:
                template_dirs.append(self.config.template_dir)
            
            # Add directory containing the template file
            if self.config.template_file:
                template_file_dir = os.path.dirname(os.path.abspath(self.config.template_file))
                if template_file_dir not in template_dirs:
                    template_dirs.append(template_file_dir)
            
            # Default to current directory if no directories specified
            if not template_dirs:
                template_dirs.append('.')
            
            self._env_cache = Environment(
                loader=FileSystemLoader(template_dirs),
                autoescape=select_autoescape(['html', 'xml']),
                cache_size=100,  # Enable template caching
                auto_reload=True  # Enable auto-reload for development
            )
        
        return self._env_cache
    
    def render_template(self, template_path: str, context: Dict[str, Any]) -> str:
        """Render template with high performance."""
        env = self._get_environment()
        
        # Get template name relative to template directories
        template_name = os.path.basename(template_path)
        
        # Check if we have a cached version and if the template file is newer
        template_path_abs = os.path.abspath(template_path)
        cache_key = template_path_abs
        
        if cache_key in self._template_cache:
            cached_template, cached_mtime = self._template_cache[cache_key]
            current_mtime = os.path.getmtime(template_path_abs)
            
            if current_mtime <= cached_mtime:
                # Use cached template
                return cached_template.render(context)
        
        # Load and render template
        template = env.get_template(template_name)
        rendered = template.render(context)
        
        # Cache the rendered result with modification time
        self._template_cache[cache_key] = (template, os.path.getmtime(template_path_abs))
        
        return rendered


class FileWatcher(FileSystemEventHandler):
    """High-performance file watcher with debouncing."""
    
    def __init__(self, config: WeeConfig, renderer: TemplateRenderer):
        self.config = config
        self.renderer = renderer
        self.last_render_time = 0
        self.pending_render = False
        self.observer = Observer()
        
    def start_watching(self):
        """Start watching files."""
        if not WATCHDOG_AVAILABLE:
            print("ERROR: Watch mode requires 'watchdog' package")
            sys.exit(1)
        
        # Watch template directory
        watch_paths = set()
        
        if self.config.template_file:
            template_dir = os.path.dirname(os.path.abspath(self.config.template_file))
            watch_paths.add(template_dir)
        
        if self.config.template_dir:
            watch_paths.add(os.path.abspath(self.config.template_dir))
        
        if self.config.context_file:
            context_dir = os.path.dirname(os.path.abspath(self.config.context_file))
            watch_paths.add(context_dir)
        
        # Schedule watching for all paths
        for path in watch_paths:
            self.observer.schedule(self, path, recursive=True)
        
        self.observer.start()
        print(f"🔍 Watching {len(watch_paths)} path(s) for changes...")
        
    def stop_watching(self):
        """Stop watching files."""
        self.observer.stop()
        self.observer.join()
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Check if this is a file we care about
        should_render = False
        
        if (self.config.template_file and 
            file_path == os.path.abspath(self.config.template_file)):
            should_render = True
        elif (self.config.context_file and 
              file_path == os.path.abspath(self.config.context_file)):
            should_render = True
        elif self.config.template_dir:
            # Any file in template directory
            if file_path.startswith(os.path.abspath(self.config.template_dir)):
                should_render = True
        
        if not should_render:
            return
        
        # Debounce rapid changes
        current_time = time.time() * 1000  # Convert to milliseconds
        if current_time - self.last_render_time < self.config.debounce_ms:
            self.pending_render = True
            return
        
        self.last_render_time = current_time
        self._trigger_render(file_path)
    
    def _trigger_render(self, changed_file: str):
        """Trigger a render with updated context."""
        print(f"\n🔄 Change detected: {os.path.basename(changed_file)}")
        
        # Reload context if context file changed
        if self.config.context_file and changed_file == os.path.abspath(self.config.context_file):
            try:
                with open(self.config.context_file, 'r', encoding='utf-8') as f:
                    self.config.context_data = json.load(f)
                print("✓ Context reloaded")
            except Exception as e:
                print(f"✗ Error reloading context: {e}")
                return
        
        # Render and generate PDF
        try:
            render_and_generate_pdf(self.config, self.renderer, auto_open=self.config.auto_open)
        except Exception as e:
            print(f"✗ Error during render: {e}")


def load_context(config: WeeConfig) -> Dict[str, Any]:
    """Load context from file or use defaults."""
    if config.context_file and os.path.exists(config.context_file):
        try:
            with open(config.context_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load context file: {e}")
    
    # Default context
    return {
        'title': 'Wee Document',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'author': 'Wee User',
        'description': 'Document generated with Wee',
        'items': [
            {'name': 'Sample Item', 'quantity': 1, 'price': 9.99}
        ]
    }


def html_to_pdf(html_content: str, output_path: str):
    """Convert HTML to PDF using WeasyPrint."""
    HTML(string=html_content).write_pdf(output_path)
    print(f"✓ PDF generated: {output_path}")


def open_pdf(pdf_path: str):
    """Open PDF in default system viewer."""
    system = platform.system()
    
    try:
        if system == 'Darwin':  # macOS
            subprocess.Popen(['open', pdf_path])
        elif system == 'Windows':
            subprocess.Popen(['cmd', '/c', 'start', '/B', pdf_path], shell=True)
        else:  # Linux and other Unix-like systems
            subprocess.Popen(['xdg-open', pdf_path])
        print(f"✓ Opened PDF in default viewer")
    except Exception as e:
        print(f"⚠ Could not open PDF automatically: {e}")


def render_and_generate_pdf(config: WeeConfig, renderer: TemplateRenderer, auto_open: bool = True):
    """Render template and generate PDF."""
    print(f"📄 Rendering: {config.template_file}")
    
    # Load context
    context = load_context(config)
    
    # Render template
    html_content = renderer.render_template(config.template_file, context)
    print("✓ Template rendered")
    
    # Save HTML for debugging
    html_output = config.output_pdf.replace('.pdf', '.html')
    with open(html_output, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"✓ HTML saved: {html_output}")
    
    # Convert to PDF
    html_to_pdf(html_content, config.output_pdf)
    
    # Open PDF if requested
    if auto_open:
        open_pdf(config.output_pdf)


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        prog='wee',
        description='High-performance Jinja2 template to PDF renderer with hot-reload',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  wee                          # Show this help message
  wee -t template.html         # Render template once
  wee -t template.html -w     # Render and watch for changes
  wee -t template.html -c context.json -w  # Use context file and watch
  wee -t template.html -d templates/ -w     # Use template directory and watch
        """
    )
    
    parser.add_argument('-t', '--template', 
                       help='Template file to render')
    parser.add_argument('-d', '--template-dir',
                       help='Template directory for extending templates')
    parser.add_argument('-c', '--context',
                       help='Context JSON file (monitored in watch mode)')
    parser.add_argument('-o', '--output', default='output.pdf',
                       help='Output PDF file (default: output.pdf)')
    parser.add_argument('-w', '--watch', action='store_true',
                       help='Watch for changes and auto-regenerate')
    parser.add_argument('--no-open', action='store_true',
                       help='Do not automatically open PDF after generation')
    parser.add_argument('--debounce', type=int, default=100,
                       help='Debounce time in milliseconds for file changes (default: 100)')
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    
    # Show help if no arguments provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.template:
        print("Error: Template file is required")
        parser.print_help()
        sys.exit(1)
    
    if not os.path.exists(args.template):
        print(f"Error: Template file '{args.template}' not found!")
        sys.exit(1)
    
    if args.context and not os.path.exists(args.context):
        print(f"Warning: Context file '{args.context}' not found, using default context")
    
    if args.template_dir and not os.path.exists(args.template_dir):
        print(f"Error: Template directory '{args.template_dir}' not found!")
        sys.exit(1)
    
    # Create configuration
    config = WeeConfig()
    config.template_file = args.template
    config.template_dir = args.template_dir
    config.output_pdf = args.output
    config.context_file = args.context
    config.watch_mode = args.watch
    config.auto_open = not args.no_open
    config.debounce_ms = args.debounce
    
    # Load initial context
    config.context_data = load_context(config)
    
    # Create renderer
    renderer = TemplateRenderer(config)
    
    # Initial render
    render_and_generate_pdf(config, renderer, auto_open=config.auto_open)
    
    # Watch mode
    if config.watch_mode:
        watcher = FileWatcher(config, renderer)
        
        # Set up signal handler for graceful shutdown
        def signal_handler(signum, frame):
            print("\n\n🛑 Stopping watch mode...")
            watcher.stop_watching()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        watcher.start_watching()
        
        try:
            print("🔍 Watch mode active. Press Ctrl+C to stop.")
            while True:
                time.sleep(0.1)  # Reduced sleep time for faster response
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()
