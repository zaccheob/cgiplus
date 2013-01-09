#!/usr/bin/python
import sys, os
from cgi import FieldStorage
from cStringIO import StringIO
import logging
logging.basicConfig(level=logging.DEBUG)

HTMLTAGS = ('a', 'abbr', 'address', 'area', 'article', 'aside', 'audio', 'b', 'base', 'bdo', 'blockquote', 'body', 'br', 'button', 'canvas', 'caption', 'cite', 'code', 'col', 'colgroup', 'command', 'datalist', 'dd', 'del', 'details', 'dfn', 'div', 'dl', 'dt', 'em', 'embed', 'eventsource', 'fieldset', 'figcaption', 'figure', 'footer', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'head', 'header', 'hgroup', 'hr', 'html', 'i', 'iframe', 'img', 'input', 'ins', 'kbd', 'keygen', 'label', 'legend', 'li', 'link', 'mark', 'map', 'menu', 'meta', 'meter', 'nav', 'noscript', 'object', 'ol', 'optgroup', 'option', 'output', 'p', 'param', 'pre', 'progress', 'q', 'ruby', 'rp', 'rt', 'samp', 'script', 'section', 'select', 'small', 'source', 'span', 'strong', 'style', 'sub', 'summary', 'sup', 'table', 'tbody', 'td', 'textarea', 'tfoot', 'th', 'thead', 'time', 'title', 'tr', 'ul', 'var', 'video', 'wbr')

#Utility
def isiterable(o):
	if isinstance(o, str) or isinstance(o, unicode):
		return False
	try:
		iter(o)
		return True
	except TypeError:
		return False


class HTMLString(object):
	def __init__(self, s = ''):
		self.outbuf = StringIO()
		self.append(s)

	def _htmlattributevalue(self, value):
		if value == None:
			return '=""'
		return '="%s"' % self._htmlescape(value)

	def _htmlattributes(self, attributes):
		return ' '.join(['%s%s' % (key, self._htmlattributevalue(value)) for (key, value) in attributes.iteritems()])

	def start_tag(self, name, attrs = None, empty = False):
		self.outbuf.write('<%s' % name)
		if attrs:
			self.outbuf.write(' %s' % self._htmlattributes(attrs))
		if empty:
			self.outbuf.write('/')
		self.outbuf.write('>')
		return self

	def end_tag(self, name):
		self.outbuf.write("</%s>" % name)
		return self

	def doctype(self):
		self.outbuf.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n')
		return self

	def _htmlescape(self, s, encoding = 'utf8'):
		if isinstance(s, unicode):
			s = s.encode(encoding)
		return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

	def append(self, s):
		if isinstance(s, HTMLString):
			self.outbuf.write(str(s))
		else:
			self.outbuf.write(self._htmlescape(s))

		return self

	def __str__(self):
		return self.outbuf.getvalue()

	def __iadd__(self, s):
		self.append(s)
		return self
	

class CGI(FieldStorage):
	def __getattr__(self, a):
		if a in HTMLTAGS:
			return lambda *args: self._htmltag(a, *args)
		elif a in [ '%s_start' % x for x in HTMLTAGS ]:
			return lambda *args: self._htmltag_start(a.replace('_start', ''), *args)
		elif a in [ '%s_end' % x for x in HTMLTAGS ]:
			return lambda *args: self._htmltag_end(a.replace('_end', ''), *args)
		else:
			raise AttributeError, '%s' % a


	def _htmltag_start(self, name, attrs = None, empty = False):
		return HTMLString().start_tag(name, attrs, empty)

	def _htmltag_end(self, name):
		return HTMLString().end_tag(name)
		
	def _htmltag(self, name, *args):
		content_start = 0
		attrs = None
		if len(args) > 0 and isinstance(args[0], dict):
			attrs = args[0]
			content_start = 1
		if len(args) > content_start:
			if isiterable(args[content_start]):
				#Distributive property
				content_i = args[content_start]
				#Note che in this case every subsequent argument is ignored
			else:
				content_i = (args[content_start:],)
		else:
			out = self._htmltag_start(name, attrs, empty = True)
			return out

		out = HTMLString()
		for content in content_i:
			out += self._htmltag_start(name, attrs)

			if isiterable(content):
				for c in args[content_start:]:
					out += c
			else:
				out += content

			out += self._htmltag_end(name)

		return out

	def header(self, type='text/html'):
		return "Content-type: %s;charset=utf-8\n\n" % type

	def start_html(self, title, style = None, script = None):
		out = HTMLString()
		out.doctype()
		out += self.html_start({'xmlns': "http://www.w3.org/1999/xhtml"})
		out += self.head_start()
		out += self.title(title)
		if not isiterable(style):
			style = [style]
		for s in style:
			if isinstance(s, HTMLString):
				out += s
			else:
				out += self.link({'rel': 'stylesheet', 'type': 'text/css', 'href': s})

		if not isiterable(script):
			script = [script]
		for s in script:
			if isinstance(s, HTMLString):
				out += s
			else:
				out += self.script_start({'type': 'text/javascript', 'src':s})
				out += self.script_end()
		out += self.head_end()
		out += self.body_start()
		return out

	def end_html(self):
		out = HTMLString()
		out += self.body_end()
		out += self.html_end()
		return out

	def start_form(self, method = 'get', action = None):
		if action == None: action = os.environ.get('SCRIPT_NAME', '')
		return self.form_start({'method': method, 'action': action, 'enctype': 'multipart/form-data', 'accept-charset': 'utf-8'})

	def end_form(self):
		return self.form_end()

	#Form fields
	def textfield(self, name, value = None, size = None, maxlength = None, attrs = {} ):
		value = self.getfirst(name, value)
		attrs['type'] = 'text'
		attrs['name'] = name
		attrs['value'] = value
		return self.input(attrs)

	def passwordfield(self, name, value = None, size = None, maxlength = None):
		value = self.getfirst(name, value)
		return self.input({'type': 'password', 'name': name, 'value': value})

	def textareafield(self, name, value = None, cols = 15, rows=4):
		value = self.getfirst(name, value)
		return self.textarea({'name': name, 'cols': cols, 'rows': rows}, value)

	def popupfield(self, name, options, attrs = {}):
		selected = self.getlist(name)
		attrs['name'] = name
		out = self.select_start(attrs)
		for o in options:
			if isiterable(o) and len(o) == 2:
				value = o[0]
				text = o[1]
			else:
				value = o
				text = o
			if not isinstance(value, str) and not isinstance(value, unicode):
				value = str(value)
			attrs = {'value': value}
			if value in selected:
				attrs['selected'] = 'selected'
			out += self.option(attrs, text)
		out += self.select_end()
		return out

	def submit(self, name = "", value = "Submit"):
		return self.input({'type': 'submit', 'name': name, 'value': value})
