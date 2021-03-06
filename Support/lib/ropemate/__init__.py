import os, sys

support_lib = os.path.join(os.environ["TM_SUPPORT_PATH"], "lib")
if support_lib not in sys.path:
    sys.path.insert(0, support_lib)

import tm_helpers
import encoding

from rope.base import project,libutils

from ropemate.path import update_python_path
from rope.contrib import autoimport

class ropecontext(object):
    """a context manager to have a rope project context"""

    project = None
    resource = None
    project_dir = None
    file_path = None
    input = ""
    
    def __enter__(self):
        self.project_dir = os.environ.get('TM_PROJECT_DIRECTORY')
        self.file_path = os.environ.get('TM_FILEPATH')
        
        if self.project_dir:
            self.project = project.Project(self.project_dir)
            # no use to have auto import for a single file project
            if not os.path.exists("%s/.ropeproject/globalnames" % self.project_dir):
                importer = autoimport.AutoImport(project=self.project, observe=True)
                importer.generate_cache()
            if os.path.exists("%s/__init__.py" % self.project_dir):
                sys.path.append(self.project_dir)
            self.input = encoding.from_fs(sys.stdin.read())
            
        elif self.file_path:
            #create a single-file project (ignoring all other files in the file's folder)
            folder = os.path.dirname(self.file_path)
            ignored_res = os.listdir(folder)
            ignored_res.remove(os.path.basename(self.file_path))
            self.project = project.Project(
                ropefolder=None, projectroot=folder, ignored_resources=ignored_res)
            self.input = encoding.from_fs(sys.stdin.read())
        else:
            tm_helpers.save_current_document()
            self.file_path = os.environ.get('TM_FILEPATH')
            folder = os.path.dirname(self.file_path)
            ignored_res = os.listdir(folder)
            ignored_res.remove(os.path.basename(self.file_path))
            self.project = project.Project(
                ropefolder=None, projectroot=folder, ignored_resources=ignored_res)
            with open(self.file_path) as fs:
                self.input = encoding.from_fs(fs.read())
            
        self.resource = libutils.path_to_resource(self.project, self.file_path)
        
        update_python_path( self.project.prefs.get('python_path', []) )
        
        return self
    
    def __exit__(self, type , value , traceback):
        if type is None:
            self.project.close()

context = ropecontext()