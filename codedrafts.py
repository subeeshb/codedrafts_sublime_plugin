import sublime
import sublime_plugin
from urllib import parse, request
import json
import webbrowser
import os

HOST = 'https://codedrafts.io'

class CodedraftsUploadCommand(sublime_plugin.TextCommand):
    def get_display_filename(self, full_path):
        if full_path is None:
            return 'Untitled File'

        return os.path.split(full_path)[1]

    def get_file_type(self, full_path):
        if full_path is None:
            return 'plaintext'

        extension = os.path.splitext(full_path)[1]
        if extension in ('.js', '.jsx'):
            return 'javascript'
        elif extension == '.java':
            return 'java'
        elif extension in ('.css', '.scss', '.less'):
            return 'css'
        elif extension in ('.html', '.htm'):
            return 'html'
        elif extension == '.py':
            return 'python'
        else:
            return 'plaintext'

    def get_author(self):
        return os.path.split(os.path.expanduser('~'))[-1]

    def upload(self, filename, author, language, body, current_file_id):
        params = json.dumps({'filename': filename, 'code': body, 'language': language, 'author': author}).encode('utf8')
        hdr = {'User-Agent': 'SublimePlugin1.0',
             'Content-Type' : 'application/json',
             'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
             'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
             'Accept-Encoding': 'none',
             'Accept-Language': 'en-US,en;q=0.8',
             'Connection': 'keep-alive'}
        if current_file_id is None:
            url = '%s/api/files' % (HOST)
        else:
            url = '%s/api/files/%s/revisions' % (HOST, current_file_id)
        req = request.Request(url, data=params, headers=hdr)
        response = request.urlopen(req)
        response_body = response.read().decode('utf8')

        result = json.loads(response_body)
        if (result['success']):
            file_url = '%s/files/%s' % (HOST, result['file_id'])
            webbrowser.open_new_tab(file_url)
            self.view.settings().set('cd_file_id', result['file_id'])
            sublime.status_message('File uploaded to %s.' % file_url)
        elif current_file_id is not None:
            # could fail if previously uploaded file was deleted. try again, this time without referencing the previous file ID
            print('Failed using file_id %s, retrying to new file.' % current_file_id)
            self.upload(filename, author, language, body, None)

    def run(self, edit):
        body = self.view.substr(sublime.Region(0, self.view.size()))
        file_path = self.view.file_name()
        filename = self.get_display_filename(file_path)
        author = self.get_author()
        language = self.get_file_type(file_path)
        current_file_id = self.view.settings().get('cd_file_id')
        
        self.upload(filename, author, language, body, current_file_id)

class CodedraftsDownloadCommand(sublime_plugin.TextCommand):
    def get_headers(self):
        return {'User-Agent': 'SublimePlugin1.0',
             'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
             'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
             'Accept-Encoding': 'none',
             'Accept-Language': 'en-US,en;q=0.8',
             'Connection': 'keep-alive'}

    def get_latest_revision_id(self, file_id):
        url = '%s/api/files/%s/revisions' % (HOST, file_id)
        req = request.Request(url, headers=self.get_headers())
        response = request.urlopen(req)
        response_body = response.read().decode('utf8')
        result = json.loads(response_body)

        if result['success']:
            return result['revisions'][0]['revision_id']
        else:
            return None

    def get_revision_contents(self, file_id, revision_id):
        url = '%s/files/%s/%s/raw' % (HOST, file_id, revision_id)
        req = request.Request(url, headers=self.get_headers())
        response = request.urlopen(req)
        response_body = response.read().decode('utf8')
        return response_body

    def run(self, edit):
        current_file_id = self.view.settings().get('cd_file_id')
        if current_file_id is None:
            sublime.status_message('This file has not been uploaded to CodeDrafts yet.')
            return

        
        latest_revision = self.get_latest_revision_id(current_file_id)
        if latest_revision is None:
            sublime.status_message('Could not get the latest revision for this file. It may have been deleted.')

        latest_code = self.get_revision_contents(current_file_id, latest_revision)
        self.view.replace(edit, sublime.Region(0, self.view.size()), latest_code)
        sublime.status_message('Updated to latest revision.')
