#!/usr/bin/env python
"""
    make-flaskext
    ~~~~~~~~~~~~~

    Little helper script that helps creating new flask extensions.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
import re
import os
import sys
import getpass
from datetime import datetime
from subprocess import Popen

from jinja2 import Template
from werkzeug import url_quote


_sep_re = re.compile(r'[\s.,;_-]+')


SPHINX_THEME_REPO = 'git://github.com/mitsuhiko/flask-sphinx-themes.git'
FILE_HEADER_TEMPLATE = Template(u'''\
# -*- coding: utf-8 -*-
"""
    {{ module }}
    {{ '~' * module|length }}

    Description of the module goes here...

    :copyright: (c) {{ year }} by {{ name }}.
    :license: BSD, see LICENSE for more details.
"""
''')
BSD_LICENSE_TEMPLATE = Template(u'''\
Copyright (c) {{ year }} by {{ name }}.

Some rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above
  copyright notice, this list of conditions and the following
  disclaimer in the documentation and/or other materials provided
  with the distribution.

* The names of the contributors may not be used to endorse or
  promote products derived from this software without specific
  prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
''')

SETUP_PY_TEMPLATE = Template(u'''\
"""
{{ name }}
{{ '-' * name|length }}

Description goes here...

Links
`````

* `documentation <http://packages.python.org/{{ urlname }}>`_
{% if vcs_host in ('github', 'gitorious', 'bitbucket') -%}
* `development version
{%- if vcs_host == 'github' %}
  <http://github.com/USERNAME/REPOSITORY/zipball/master#egg={{ urlname }}-dev>`_
{%- elif vcs_host == 'gitorious' %}
  <http://gitorious.org/PROJECT/REPOSITORY/archive-tarball/master#egg={{ urlname }}-dev>`_
{%- elif vcs_host == 'bitbucket' %}
  <http://bitbucket.org/USERNAME/REPOSITORY/get/tip.gz#egg={{ urlname }}-dev`_
{% endif %}
{% endif %}
"""
from setuptools import setup


setup(
    name={{ name|pprint }},
    version='0.1',
    url='<enter URL here>',
    license='BSD',
    author={{ author|pprint }},
    author_email='your-email-here@example.com',
    description='<enter short description here>',
    long_description=__doc__,
    packages=['flaskext'],
    namespace_packages=['flaskext'],
    zip_safe=False,
    platforms='any',
    install_requires=[
        'Flask'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
''')


def prompt(name, default=None):
    prompt = name + (default and ' [%s]' % default or '')
    prompt += name.endswith('?') and ' ' or ': '
    while True:
        rv = raw_input(prompt)
        if rv:
            return rv
        if default is not None:
            return default


def prompt_bool(name, default=False):
    while True:
        rv = prompt(name + '?', default and 'Y' or 'N')
        if not rv:
            return default
        if rv.lower() in ('y', 'yes', '1', 'on', 'true', 't'):
            return True
        elif rv.lower() in ('n', 'no', '0', 'off', 'false', 'f'):
            return False


def prompt_choices(name, choices):
    while True:
        rv = prompt(name + '? - (%s)' % ', '.join(choices), choices[0])
        rv = rv.lower()
        if not rv:
            return choices[0]
        if rv in choices:
            if rv == 'none':
                return None
            else:
                return rv


def guess_package(name):
    """Guess the package name"""
    words = [x.lower() for x in _sep_re.split(name)]
    words = [x for x in words if x != 'flask']
    return '_'.join(words) or None


class Extension(object):

    def __init__(self, name, shortname, author, output_folder, vcs, vcs_host,
                 with_sphinx, sphinx_theme):
        self.name = name
        self.shortname = shortname
        self.author = author
        self.output_folder = output_folder
        self.vcs = vcs
        self.vcs_host = vcs_host
        self.with_sphinx = with_sphinx
        self.sphinx_theme = sphinx_theme

    def make_folder(self):
        os.makedirs(os.path.join(self.output_folder, 'flaskext'))

    def create_files(self):
        with open(os.path.join(self.output_folder, 'flaskext',
                               '__init__.py'), 'w') as f:
            f.write("__import__('pkg_resources')."
                    "declare_namespace(__name__)\n")
        with open(os.path.join(self.output_folder, 'flaskext',
                               self.shortname + '.py'), 'w') as f:
            f.write(FILE_HEADER_TEMPLATE.render(
                module='flaskext.' + self.shortname,
                year=datetime.utcnow().year,
                name=self.author
            ).encode('utf-8') + '\n')
        with open(os.path.join(self.output_folder, 'LICENSE'), 'w') as f:
            f.write(BSD_LICENSE_TEMPLATE.render(
                year=datetime.utcnow().year,
                name=self.author
            ).encode('utf-8') + '\n')
        with open(os.path.join(self.output_folder, 'README'), 'w') as f:
            f.write(self.name + '\n\nDescription goes here\n')
        with open(os.path.join(self.output_folder, 'setup.py'), 'w') as f:
            f.write(SETUP_PY_TEMPLATE.render(
                name=self.name,
                urlname=url_quote(self.name),
                package='flaskext.' + self.shortname,
                author=self.author,
                vcs_host=self.vcs_host
            ).encode('utf-8') + '\n')

    def init_vcs(self):
        if self.vcs == 'hg':
            self.init_hg()
        elif self.vcs == 'git':
            self.init_git()

    def init_hg(self):
        Popen(['hg', 'init'], cwd=self.output_folder).wait()

    def init_git(self):
        Popen(['git', 'init'], cwd=self.output_folder).wait()
        if self.with_sphinx:
            Popen(['git', 'submodule', 'add', SPHINX_THEME_REPO,
                   'docs/_themes'], cwd=self.output_folder).wait()

    def init_sphinx(self):
        if not self.with_sphinx:
            return
        docdir = os.path.join(self.output_folder, 'docs')
        os.makedirs(docdir)
        Popen(['sphinx-quickstart'], cwd=docdir).wait()
        with open(os.path.join(docdir, 'conf.py'), 'r') as f:
            config = f.read().splitlines()
            for idx, line in enumerate(config):
                if line.startswith('#sys.path.append'):
                    config[idx] = "sys.path.append(os.path.abspath('_themes'))"
                elif line.startswith('html_theme ='):
                    config[idx] = 'html_theme = %r' % self.sphinx_theme
                elif line == '#html_theme_path = []':
                    config[idx] = "html_theme_path = ['_themes']"
                elif line.startswith('pygments_style ='):
                    config[idx] = "#pygments_style = 'sphinx'"
        with open(os.path.join(docdir, 'conf.py'), 'w') as f:
            f.write('\n'.join(config))
        if not self.vcs == 'git':
            print 'Don\'t forget to put the sphinx themes into docs/_themes!'


def main():
    if len(sys.argv) not in (1, 2):
        print 'usage: make-flaskext.py [output-folder]'
        return
    print 'Welcome to the Flask Extension Creator Wizard'
    print

    while 1:
        name = prompt('Extension Name (human readable)')
        if 'flask' in name.lower():
            break
        if prompt_bool('Warning: It\'s recommended that the extension name '
                       'contains the word "Flask". Continue'):
            break
    shortname = prompt('Shortname (without flaskext.)', default=guess_package(name))
    author = prompt('Author', default=getpass.getuser())
    use_sphinx = prompt_bool('Create sphinx documentation', default=True)
    sphinx_theme = None
    if use_sphinx:
        sphinx_theme = prompt('Sphinx theme to use', default='flask_small')
    vcs = prompt_choices('Which VCS to use', ('none', 'git', 'hg'))
    if vcs is None:
        vcs_host = None
    elif vcs == 'git':
        vcs_host = prompt_choices('Which git host to use',
                                  ('none', 'github', 'gitorious'))
    elif vcs == 'hg':
        vcs_host = prompt_choices('Which Mercurial host to use',
                                  ('none', 'bitbucket'))

    output_folder = len(sys.argv) == 2 and sys.argv[1] or ('flask-%s' % shortname)
    while 1:
        folder = prompt('Output folder', default=output_folder)
        if os.path.isfile(folder):
            print 'Error: output folder is a file'
        elif os.path.isdir(folder) and os.listdir(folder):
            if prompt_bool('Warning: output folder is not empty. Continue'):
                break
        else:
            break
    output_folder = os.path.abspath(folder)

    ext = Extension(name, shortname, author, output_folder, vcs, vcs_host,
                    use_sphinx, sphinx_theme)
    ext.make_folder()
    ext.create_files()
    ext.init_sphinx()
    ext.init_vcs()


if __name__ == '__main__':
    main()
