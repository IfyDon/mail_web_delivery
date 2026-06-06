"""Template rendering service.

Provides rendering of TemplateVersion objects with Jinja2 substitution
and optional MJML -> HTML compilation when `mjml` is available on PATH.
"""

from typing import Dict
import subprocess
import tempfile

from jinja2 import Environment, BaseLoader, StrictUndefined


def _compile_mjml_to_html(mjml_source: str) -> str:
	"""Attempt to compile MJML source to HTML using the `mjml` CLI.

	Raises RuntimeError if compilation fails or mjml is not available.
	"""
	with tempfile.NamedTemporaryFile(mode="w+", suffix=".mjml", delete=False) as in_f:
		in_f.write(mjml_source)
		in_f.flush()
		in_path = in_f.name

	out_f = tempfile.NamedTemporaryFile(mode="r", suffix=".html", delete=False)
	out_path = out_f.name
	out_f.close()

	try:
		proc = subprocess.run(["mjml", in_path, "-o", out_path], capture_output=True, text=True, timeout=10)
		if proc.returncode != 0:
			raise RuntimeError(proc.stderr or "mjml failed")
		with open(out_path, "r", encoding="utf-8") as fh:
			return fh.read()
	finally:
		try:
			import os

			os.unlink(in_path)
			os.unlink(out_path)
		except Exception:
			pass


def render_template(version, context: Dict[str, str] | None = None, compile_mjml: bool = False) -> Dict[str, str]:
	"""Render a TemplateVersion with the provided context.

	Returns a dict: {"html": ..., "text": ...}
	"""
	env = Environment(loader=BaseLoader(), undefined=StrictUndefined)
	ctx = context or {}

	# Render text content
	text = ""
	if getattr(version, "text_content", None):
		tmpl = env.from_string(version.text_content)
		text = tmpl.render(**ctx)

	# Render HTML or MJML
	html = ""
	source = getattr(version, "html_content", None) or getattr(version, "mjml_source", None) or ""
	if source:
		tmpl = env.from_string(source)
		rendered = tmpl.render(**ctx)
		if compile_mjml and getattr(version, "mjml_source", None):
			try:
				html = _compile_mjml_to_html(rendered)
			except Exception:
				# Fallback to the rendered source if mjml not available
				html = rendered
		else:
			html = rendered

	return {"html": html, "text": text}

