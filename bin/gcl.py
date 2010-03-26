#!/usr/bin/python
# Copyright (c) 2006-2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Wrapper script around Rietveld's upload.py that groups files into
# changelists.

import getpass
import linecache
import os
import random
import re
import string
import subprocess
import sys
import tempfile
import upload
import urllib2

CODEREVIEW_SETTINGS = {
  # Default values.
  "CODE_REVIEW_SERVER": "rietku.appspot.com",
  "CC_LIST": "jaikuengine-reviews@googlegroups.com",
  "VIEW_VC": "http://code.google.com/p/jaikuengine/source/detail?r=",
}

# Use a shell for subcommands on Windows to get a PATH search, and because svn
# may be a batch file.
use_shell = sys.platform.startswith("win")

# globals that store the root of the current repository and the directory where
# we store information about changelists.
repository_root = ""
gcl_info_dir = ""

# Filename where we store repository specific information for gcl.
CODEREVIEW_SETTINGS_FILE = "codereview.settings"

# Warning message when the change appears to be missing tests.
MISSING_TEST_MSG = "Change contains new or modified methods, but no new tests!"

# Caches whether we read the codereview.settings file yet or not.
read_gcl_info = False


def DiffPrint(filename):
  """Return file content in unified diff format as though it's been added"""
  # The file is "new" in the patch sense. Generate a homebrew diff.
  # We can't use ReadFile() since it's not using binary mode.
  file_handle = open(filename, 'rb')
  file_content = file_handle.read()
  file_handle.close()
  # Prepend '+ ' to every lines.
  file_content = ['+ ' + i for i in file_content.splitlines(True)]
  nb_lines = len(file_content)
  # We need to use / since patch on unix will fail otherwise.
  filename = filename.replace('\\', '/')
  data = "Index: %s\n" % filename
  data += ("============================================================="
           "======\n")
  # Note: Should we use /dev/null instead?
  data += "--- %s\n" % filename
  data += "+++ %s\n" % filename
  data += "@@ -0,0 +1,%d @@\n" % nb_lines
  data += ''.join(file_content)
  return data


def IsSVNMoved(filename):
  """Determine if a file has been added through svn mv"""
  info = GetSVNFileInfo(filename)
  return (info.get('Copied From URL') and
          info.get('Copied From Rev') and
          info.get('Schedule') == 'add')


def GetSVNFileInfo(file):
  """Returns a dictionary from the svn info output for the given file."""
  output = RunShell(["svn", "info", file])
  result = {}
  re_key_value_pair = re.compile('^(.*)\: (.*)$')
  for line in output.splitlines():
    key_value_pair = re_key_value_pair.match(line)
    if key_value_pair:
      result[key_value_pair.group(1)] = key_value_pair.group(2)
  return result


def GetSVNFileProperty(file, property_name):
  """Returns the value of an SVN property for the given file.

  Args:
    file: The file to check
    property_name: The name of the SVN property, e.g. "svn:mime-type"

  Returns:
    The value of the property, which will be the empty string if the property
    is not set on the file.  If the file is not under version control, the
    empty string is also returned.
  """
  output = RunShell(["svn", "propget", property_name, file])
  if (output.startswith("svn: ") and
      output.endswith("is not under version control")):
    return ""
  else:
    return output


def GetRepositoryRoot():
  """Returns the top level directory of the current repository.

  The directory is returned as an absolute path.
  """
  global repository_root
  if not repository_root:
    cur_dir_repo_root = GetSVNFileInfo(os.getcwd()).get("Repository Root")
    if not cur_dir_repo_root:
      ErrorExit("gcl run outside of repository")

    repository_root = os.getcwd()
    while True:
      parent = os.path.dirname(repository_root)
      if GetSVNFileInfo(parent).get("Repository Root") != cur_dir_repo_root:
        break
      repository_root = parent
  return repository_root


def GetInfoDir():
  """Returns the directory where gcl info files are stored."""
  global gcl_info_dir
  if not gcl_info_dir:
    gcl_info_dir = os.path.join(GetRepositoryRoot(), '.svn', 'gcl_info')
  return gcl_info_dir


def GetCodeReviewSetting(key):
  """Returns a value for the given key for this repository."""
  global read_gcl_info
  if not read_gcl_info:
    read_gcl_info = True
    # First we check if we have a cached version.
    cached_settings_file = os.path.join(GetInfoDir(), CODEREVIEW_SETTINGS_FILE)
    if (not os.path.exists(cached_settings_file) or
        os.stat(cached_settings_file).st_mtime > 60*60*24*3):
      dir_info = GetSVNFileInfo(".")
      repo_root = dir_info["Repository Root"]
      url_path = dir_info["URL"]
      settings = ""
      while True:
        # Look for the codereview.settings file at the current level.
        svn_path = url_path + "/" + CODEREVIEW_SETTINGS_FILE
        settings, rc = RunShellWithReturnCode(["svn", "cat", svn_path])
        if not rc:
          # Exit the loop if the file was found.
          break
        # Make sure to mark settings as empty if not found.
        settings = ""
        if url_path == repo_root:
          # Reached the root. Abandoning search.
          break;
        # Go up one level to try again.
        url_path = os.path.dirname(url_path)

      # Write a cached version even if there isn't a file, so we don't try to
      # fetch it each time.
      WriteFile(cached_settings_file, settings)

    output = ReadFile(cached_settings_file)
    for line in output.splitlines():
      if not line or line.startswith("#"):
        continue
      k, v = line.split(": ", 1)
      CODEREVIEW_SETTINGS[k] = v
  return CODEREVIEW_SETTINGS.get(key, "")


def IsTreeOpen():
  """Fetches the tree status and returns either True or False."""
  url = GetCodeReviewSetting('STATUS')
  status = ""
  if url:
    status = urllib2.urlopen(url).read()
  return status.find('0') == -1


def Warn(msg):
  ErrorExit(msg, exit=False)


def ErrorExit(msg, exit=True):
  """Print an error message to stderr and optionally exit."""
  print >>sys.stderr, msg
  if exit:
    sys.exit(1)


def RunShellWithReturnCode(command, print_output=False):
  """Executes a command and returns the output and the return code."""
  p = subprocess.Popen(command, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, shell=use_shell,
                       universal_newlines=True)
  if print_output:
    output_array = []
    while True:
      line = p.stdout.readline()
      if not line:
        break
      if print_output:
        print line.strip('\n')
      output_array.append(line)
    output = "".join(output_array)
  else:
    output = p.stdout.read()
  p.wait()
  p.stdout.close()
  return output, p.returncode


def RunShell(command, print_output=False):
  """Executes a command and returns the output."""
  return RunShellWithReturnCode(command, print_output)[0]


def ReadFile(filename):
  """Returns the contents of a file."""
  file = open(filename, 'r')
  result = file.read()
  file.close()
  return result


def WriteFile(filename, contents):
  """Overwrites the file with the given contents."""
  file = open(filename, 'w')
  file.write(contents)
  file.close()


class ChangeInfo:
  """Holds information about a changelist.

    issue: the Rietveld issue number, of "" if it hasn't been uploaded yet.
    description: the description.
    files: a list of 2 tuple containing (status, filename) of changed files,
           with paths being relative to the top repository directory.
  """
  def __init__(self, name="", issue="", description="", files=[]):
    self.name = name
    self.issue = issue
    self.description = description
    self.files = files
    self.patch = None

  def FileList(self):
    """Returns a list of files."""
    return [file[1] for file in self.files]

  def _NonDeletedFileList(self):
    """Returns a list of files in this change, not including deleted files."""
    return [file[1] for file in self.files if not file[0].startswith("D")]

  def _AddedFileList(self):
    """Returns a list of files added in this change."""
    return [file[1] for file in self.files if file[0].startswith("A")]

  def Save(self):
    """Writes the changelist information to disk."""
    data = SEPARATOR.join([self.issue,
                          "\n".join([f[0] + f[1] for f in self.files]),
                          self.description])
    WriteFile(GetChangelistInfoFile(self.name), data)

  def Delete(self):
    """Removes the changelist information from disk."""
    os.remove(GetChangelistInfoFile(self.name))

  def CloseIssue(self):
    """Closes the Rietveld issue for this changelist."""
    data = [("description", self.description),]
    ctype, body = upload.EncodeMultipartFormData(data, [])
    SendToRietveld("/" + self.issue + "/close", body, ctype)

  def UpdateRietveldDescription(self):
    """Sets the description for an issue on Rietveld."""
    data = [("description", self.description),]
    ctype, body = upload.EncodeMultipartFormData(data, [])
    SendToRietveld("/" + self.issue + "/description", body, ctype)

  def GetMoved(self, root=None):
    """Return a list of files that have been added through svn mv"""
    moved = [f[1] for f in self.files if IsSVNMoved(f[1])]
    if root:
      moved = [os.path.join(root, f) for f in moved]
      return moved

  def MissingTests(self):
    """Returns True if the change looks like it needs unit tests but has none.

    A change needs unit tests if it contains any new source files or methods.
    """
    SOURCE_SUFFIXES = [".cc", ".cpp", ".c", ".m", ".mm"]
    # Ignore third_party entirely.
    files = [file for file in self._NonDeletedFileList()
             if file.find("third_party") == -1]
    added_files = [file for file in self._AddedFileList()
                   if file.find("third_party") == -1]

    # If the change is entirely in third_party, we're done.
    if len(files) == 0:
      return False

    # Any new or modified test files?
    # A test file's name ends with "test.*" or "tests.*".
    test_files = [test for test in files
                  if os.path.splitext(test)[0].rstrip("s").endswith("test")]
    if len(test_files) > 0:
      return False

    # Any new source files?
    source_files = [file for file in added_files
                    if os.path.splitext(file)[1] in SOURCE_SUFFIXES]
    if len(source_files) > 0:
      return True

    # Do the long test, checking the files for new methods.
    return self._HasNewMethod()

  def _HasNewMethod(self):
    """Returns True if the changeset contains any new functions, or if a
    function signature has been changed.

    A function is identified by starting flush left, containing a "(" before
    the next flush-left line, and either ending with "{" before the next
    flush-left line or being followed by an unindented "{".

    Currently this returns True for new methods, new static functions, and
    methods or functions whose signatures have been changed.

    Inline methods added to header files won't be detected by this. That's
    acceptable for purposes of determining if a unit test is needed, since
    inline methods should be trivial.
    """
    # To check for methods added to source or header files, we need the diffs.
    # We'll generate them all, since there aren't likely to be many files
    # apart from source and headers; besides, we'll want them all if we're
    # uploading anyway.
    if self.patch is None:
      self.patch = GenerateDiff(self.FileList())

    definition = ""
    for line in self.patch.splitlines():
      if not line.startswith("+"):
        continue
      line = line.strip("+").rstrip(" \t")
      # Skip empty lines, comments, and preprocessor directives.
      # TODO(pamg): Handle multiline comments if it turns out to be a problem.
      if line == "" or line.startswith("/") or line.startswith("#"):
        continue

      # A possible definition ending with "{" is complete, so check it.
      if definition.endswith("{"):
        if definition.find("(") != -1:
          return True
        definition = ""

      # A { or an indented line, when we're in a definition, continues it.
      if (definition != "" and
          (line == "{" or line.startswith(" ") or line.startswith("\t"))):
        definition += line

      # A flush-left line starts a new possible function definition.
      elif not line.startswith(" ") and not line.startswith("\t"):
        definition = line

    return False


SEPARATOR = "\n-----\n"
# The info files have the following format:
# issue_id\n
# SEPARATOR\n
# filepath1\n
# filepath2\n
# .
# .
# filepathn\n
# SEPARATOR\n
# description


def GetChangelistInfoFile(changename):
  """Returns the file that stores information about a changelist."""
  if not changename or re.search(r'[^\w-]', changename):
    ErrorExit("Invalid changelist name: " + changename)
  return os.path.join(GetInfoDir(), changename)


def LoadChangelistInfoForMultiple(changenames, fail_on_not_found=True,
                                  update_status=False):
  """Loads many changes and merge their files list into one pseudo change.

  This is mainly usefull to concatenate many changes into one for a 'gcl try'.
  """
  changes = changenames.split(',')
  aggregate_change_info = ChangeInfo(name=changenames)
  for change in changes:
    aggregate_change_info.files += LoadChangelistInfo(change,
                                                      fail_on_not_found,
                                                      update_status).files
  return aggregate_change_info


def LoadChangelistInfo(changename, fail_on_not_found=True,
                       update_status=False):
  """Gets information about a changelist.

  Args:
    fail_on_not_found: if True, this function will quit the program if the
      changelist doesn't exist.
    update_status: if True, the svn status will be updated for all the files
      and unchanged files will be removed.

  Returns: a ChangeInfo object.
  """
  info_file = GetChangelistInfoFile(changename)
  if not os.path.exists(info_file):
    if fail_on_not_found:
      ErrorExit("Changelist " + changename + " not found.")
    return ChangeInfo(changename)
  data = ReadFile(info_file)
  split_data = data.split(SEPARATOR, 2)
  if len(split_data) != 3:
    os.remove(info_file)
    ErrorExit("Changelist file %s was corrupt and deleted" % info_file)
  issue = split_data[0]
  files = []
  for line in split_data[1].splitlines():
    status = line[:7]
    file = line[7:]
    files.append((status, file))
  description = split_data[2]
  save = False
  if update_status:
    for file in files:
      filename = os.path.join(GetRepositoryRoot(), file[1])
      status = RunShell(["svn", "status", filename])[:7]
      if not status:  # File has been reverted.
        save = True
        files.remove(file)
      elif status != file[0]:
        save = True
        files[files.index(file)] = (status, file[1])
  change_info = ChangeInfo(changename, issue, description, files)
  if save:
    change_info.Save()
  return change_info


def GetCLs():
  """Returns a list of all the changelists in this repository."""
  cls = os.listdir(GetInfoDir())
  if CODEREVIEW_SETTINGS_FILE in cls:
    cls.remove(CODEREVIEW_SETTINGS_FILE)
  return cls


def GenerateChangeName():
  """Generate a random changelist name."""
  random.seed()
  current_cl_names = GetCLs()
  while True:
    cl_name = (random.choice(string.ascii_lowercase) +
               random.choice(string.digits) +
               random.choice(string.ascii_lowercase) +
               random.choice(string.digits))
    if cl_name not in current_cl_names:
      return cl_name


def GetModifiedFiles():
  """Returns a set that maps from changelist name to (status,filename) tuples.

  Files not in a changelist have an empty changelist name.  Filenames are in
  relation to the top level directory of the current repository.  Note that
  only the current directory and subdirectories are scanned, in order to
  improve performance while still being flexible.
  """
  files = {}

  # Since the files are normalized to the root folder of the repositary, figure
  # out what we need to add to the paths.
  dir_prefix = os.getcwd()[len(GetRepositoryRoot()):].strip(os.sep)

  # Get a list of all files in changelists.
  files_in_cl = {}
  for cl in GetCLs():
    change_info = LoadChangelistInfo(cl)
    for status, filename in change_info.files:
      files_in_cl[filename] = change_info.name

  # Get all the modified files.
  status = RunShell(["svn", "status"])
  for line in status.splitlines():
    if not len(line) or line[0] == "?":
      continue
    status = line[:7]
    filename = line[7:]
    if dir_prefix:
      filename = os.path.join(dir_prefix, filename)
    change_list_name = ""
    if filename in files_in_cl:
      change_list_name = files_in_cl[filename]
    files.setdefault(change_list_name, []).append((status, filename))

  return files


def GetFilesNotInCL():
  """Returns a list of tuples (status,filename) that aren't in any changelists.

  See docstring of GetModifiedFiles for information about path of files and
  which directories are scanned.
  """
  modified_files = GetModifiedFiles()
  if "" not in modified_files:
    return []
  return modified_files[""]


def SendToRietveld(request_path, payload=None,
                   content_type="application/octet-stream", timeout=None):
  """Send a POST/GET to Rietveld.  Returns the response body."""
  def GetUserCredentials():
    """Prompts the user for a username and password."""
    email = upload.GetEmail()
    password = getpass.getpass("Password for %s: " % email)
    return email, password

  server = GetCodeReviewSetting("CODE_REVIEW_SERVER")
  rpc_server = upload.HttpRpcServer(server,
                                    GetUserCredentials,
                                    host_override=server,
                                    save_cookies=True)
  try:
    return rpc_server.Send(request_path, payload, content_type, timeout)
  except urllib2.URLError, e:
    if timeout is None:
      ErrorExit("Error accessing url %s" % request_path)
    else:
      return None


def GetIssueDescription(issue):
  """Returns the issue description from Rietveld."""
  return SendToRietveld("/" + issue + "/description")


def UnknownFiles(extra_args):
  """Runs svn status and prints unknown files.

  Any args in |extra_args| are passed to the tool to support giving alternate
  code locations.
  """
  args = ["svn", "status"]
  args += extra_args
  p = subprocess.Popen(args, stdout = subprocess.PIPE,
                       stderr = subprocess.STDOUT, shell = use_shell)
  while 1:
    line = p.stdout.readline()
    if not line:
      break
    if line[0] != '?':
      continue  # Not an unknown file to svn.
    # The lines look like this:
    # "?      foo.txt"
    # and we want just "foo.txt"
    print line[7:].strip()
  p.wait()
  p.stdout.close()


def Opened():
  """Prints a list of modified files in the current directory down."""
  files = GetModifiedFiles()
  cl_keys = files.keys()
  cl_keys.sort()
  for cl_name in cl_keys:
    if cl_name:
      note = ""
      if len(LoadChangelistInfo(cl_name).files) != len(files[cl_name]):
        note = " (Note: this changelist contains files outside this directory)"
      print "\n--- Changelist " + cl_name + note + ":"
    for file in files[cl_name]:
      print "".join(file)


def Help(argv=None):
  if argv and  argv[0] == 'try':
    TryChange(None, ['--help'])
    return

  print (
"""GCL is a wrapper for Subversion that simplifies working with groups of files.

Basic commands:
-----------------------------------------
   gcl change change_name
      Add/remove files to a changelist. Only scans the current directory and
      subdirectories.

   gcl upload change_name [-r reviewer1@gmail.com,reviewer2@gmail.com,...]
                          [--send_mail] [--no_try] [--no_presubmit]
      Uploads the changelist to the server for review.

   gcl commit change_name [--force]
      Commits the changelist to the repository.

   gcl lint change_name
      Check all the files in the changelist for possible style violations.

Advanced commands:
-----------------------------------------
   gcl delete change_name
      Deletes a changelist.

   gcl diff change_name
      Diffs all files in the changelist.

   gcl presubmit change_name
      Runs presubmit checks without uploading the changelist.

   gcl diff
      Diffs all files in the current directory and subdirectories that aren't in
      a changelist.

   gcl changes
      Lists all the the changelists and the files in them.

   gcl nothave [optional directory]
      Lists files unknown to Subversion.

   gcl opened
      Lists modified files in the current directory and subdirectories.

   gcl settings
      Print the code review settings for this directory.

   gcl status
      Lists modified and unknown files in the current directory and
      subdirectories.

   gcl try change_name
      Sends the change to the tryserver so a trybot can do a test run on your
      code. To send multiple changes as one path, use a comma-separated list
      of changenames.
      --> Use 'gcl help try' for more information.
""")

def GetEditor():
  editor = os.environ.get("SVN_EDITOR")
  if not editor:
    editor = os.environ.get("EDITOR")

  if not editor:
    if sys.platform.startswith("win"):
      editor = "notepad"
    else:
      editor = "vi"

  return editor


def GenerateDiff(files, root=None):
  """Returns a string containing the diff for the given file list.

  The files in the list should either be absolute paths or relative to the
  given root. If no root directory is provided, the repository root will be
  used.
  """
  previous_cwd = os.getcwd()
  if root is None:
    os.chdir(GetRepositoryRoot())
  else:
    os.chdir(root)

  diff = []
  for file in files:
    # Use svn info output instead of os.path.isdir because the latter fails
    # when the file is deleted.
    if GetSVNFileInfo(file).get("Node Kind") == "directory":
      continue
    # If the user specified a custom diff command in their svn config file,
    # then it'll be used when we do svn diff, which we don't want to happen
    # since we want the unified diff.  Using --diff-cmd=diff doesn't always
    # work, since they can have another diff executable in their path that
    # gives different line endings.  So we use a bogus temp directory as the
    # config directory, which gets around these problems.
    if sys.platform.startswith("win"):
      parent_dir = tempfile.gettempdir()
    else:
      parent_dir = sys.path[0]  # tempdir is not secure.
    bogus_dir = os.path.join(parent_dir, "temp_svn_config")
    if not os.path.exists(bogus_dir):
      os.mkdir(bogus_dir)
    diff.append(RunShell(["svn", "diff", "--config-dir", bogus_dir, file]))
  os.chdir(previous_cwd)
  return "".join(diff)


def UploadCL(change_info, args):
  if not change_info.FileList():
    print "Nothing to upload, changelist is empty."
    return

  if not "--no_presubmit" in args:
    if not DoPresubmitChecks(change_info, committing=False):
      return
  else:
    args.remove("--no_presubmit")

  no_try = "--no_try" in args
  if no_try:
    args.remove("--no_try")
  else:
    # Support --no-try as --no_try
    no_try = "--no-try" in args
    if no_try:
      args.remove("--no-try")

  # Map --send-mail to --send_mail
  if "--send-mail" in args:
    args.remove("--send-mail")
    args.append("--send_mail")

  # TODO(pamg): Do something when tests are missing. The plan is to upload a
  # message to Rietveld and have it shown in the UI attached to this patch.

  upload_arg = ["upload.py", "-y"]
  upload_arg.append("--server=" + GetCodeReviewSetting("CODE_REVIEW_SERVER"))
  upload_arg.extend(args)

  desc_file = ""
  if change_info.issue:  # Uploading a new patchset.
    found_message = False
    for arg in args:
      if arg.startswith("--message") or arg.startswith("-m"):
        found_message = True
        break

    if not found_message:
      upload_arg.append("--message=''")

    upload_arg.append("--issue=" + change_info.issue)
  else: # First time we upload.
    handle, desc_file = tempfile.mkstemp(text=True)
    os.write(handle, change_info.description)
    os.close(handle)

    upload_arg.append("--cc=" + GetCodeReviewSetting("CC_LIST"))
    upload_arg.append("--description_file=" + desc_file + "")
    if change_info.description:
      subject = change_info.description[:77]
      if subject.find("\r\n") != -1:
        subject = subject[:subject.find("\r\n")]
      if subject.find("\n") != -1:
        subject = subject[:subject.find("\n")]
      if len(change_info.description) > 77:
        subject = subject + "..."
      upload_arg.append("--message=" + subject)

  # Change the current working directory before calling upload.py so that it
  # shows the correct base.
  previous_cwd = os.getcwd()
  os.chdir(GetRepositoryRoot())

  # If we have a lot of files with long paths, then we won't be able to fit
  # the command to "svn diff".  Instead, we generate the diff manually for
  # each file and concatenate them before passing it to upload.py.
  if change_info.patch is None:
    change_info.patch = GenerateDiff(change_info.FileList())
  issue, patchset = upload.RealMain(upload_arg, change_info.patch)
  if issue and issue != change_info.issue:
    change_info.issue = issue
    change_info.Save()

  if desc_file:
    os.remove(desc_file)

  # Do background work on Rietveld to lint the file so that the results are
  # ready when the issue is viewed.
  SendToRietveld("/lint/issue%s_%s" % (issue, patchset), timeout=0.5)

  # Once uploaded to Rietveld, send it to the try server.
  if not no_try and GetCodeReviewSetting('TRY_ON_UPLOAD').lower() == 'true':
    # Use the local diff.
    TryChange(change_info, [], True)

  os.chdir(previous_cwd)


def PresubmitCL(change_info):
  """Reports what presubmit checks on the change would report."""
  if not change_info.FileList():
    print "Nothing to presubmit check, changelist is empty."
    return

  print "*** Presubmit checks for UPLOAD would report: ***"
  DoPresubmitChecks(change_info, committing=False)

  print "\n\n*** Presubmit checks for COMMIT would report: ***"
  DoPresubmitChecks(change_info, committing=True)


def TryChange(change_info, args, swallow_exception=False, patchset=None):
  """Create a diff file of change_info and send it to the try server."""
  try:
    import trychange
  except ImportError:
    if swallow_exception:
      return
    ErrorExit("You need to install trychange.py to use the try server.")

  if change_info:
    trychange.TryChange(args, change_info.name, change_info.FileList(),
                        swallow_exception, patchset)
  else:
    trychange.TryChange(args)


def Commit(change_info, args):
  if not change_info.FileList():
    print "Nothing to commit, changelist is empty."
    return

  if not "--no_presubmit" in args:
    if not DoPresubmitChecks(change_info, committing=True):
      return
  else:
    args.remove("--no_presubmit")

  no_tree_status_check = ("--force" in args or "-f" in args)
  if not no_tree_status_check and not IsTreeOpen():
    print ("Error: The tree is closed. Try again later or use --force to force"
           " the commit. May the --force be with you.")
    return

  commit_cmd = ["svn", "commit"]
  filename = ''
  if change_info.issue:
    # Get the latest description from Rietveld.
    change_info.description = GetIssueDescription(change_info.issue)

  commit_message = change_info.description.replace('\r\n', '\n')
  if change_info.issue:
    commit_message += ('\nReview URL: http://%s/%s' %
                       (GetCodeReviewSetting("CODE_REVIEW_SERVER"),
                        change_info.issue))

  handle, commit_filename = tempfile.mkstemp(text=True)
  os.write(handle, commit_message)
  os.close(handle)

  handle, targets_filename = tempfile.mkstemp(text=True)
  os.write(handle, "\n".join(change_info.FileList()))
  os.close(handle)

  commit_cmd += ['--file=' + commit_filename]
  commit_cmd += ['--targets=' + targets_filename]
  # Change the current working directory before calling commit.
  previous_cwd = os.getcwd()
  os.chdir(GetRepositoryRoot())
  output = RunShell(commit_cmd, True)
  os.remove(commit_filename)
  os.remove(targets_filename)
  if output.find("Committed revision") != -1:
    change_info.Delete()

    if change_info.issue:
      revision = re.compile(".*?\nCommitted revision (\d+)",
                            re.DOTALL).match(output).group(1)
      viewvc_url = GetCodeReviewSetting("VIEW_VC")
      change_info.description = (change_info.description +
                                 "\n\nCommitted: " + viewvc_url + revision)
      change_info.CloseIssue()
  os.chdir(previous_cwd)


def Change(change_info):
  """Creates/edits a changelist."""
  if change_info.issue:
    try:
      description = GetIssueDescription(change_info.issue)
    except urllib2.HTTPError, err:
      if err.code == 404:
        # The user deleted the issue in Rietveld, so forget the old issue id.
        description = change_info.description
        change_info.issue = ""
        change_info.Save()
      else:
        ErrorExit("Error getting the description from Rietveld: " + err)
  else:
    description = change_info.description

  other_files = GetFilesNotInCL()

  separator1 = ("\n---All lines above this line become the description.\n"
                "---Repository Root: " + GetRepositoryRoot() + "\n"
                "---Paths in this changelist (" + change_info.name + "):\n")
  separator2 = "\n\n---Paths modified but not in any changelist:\n\n"
  text = (description + separator1 + '\n' +
          '\n'.join([f[0] + f[1] for f in change_info.files]) + separator2 +
          '\n'.join([f[0] + f[1] for f in other_files]) + '\n')

  handle, filename = tempfile.mkstemp(text=True)
  os.write(handle, text)
  os.close(handle)

  os.system(GetEditor() + " " + filename)

  result = ReadFile(filename)
  os.remove(filename)

  if not result:
    return

  split_result = result.split(separator1, 1)
  if len(split_result) != 2:
    ErrorExit("Don't modify the text starting with ---!\n\n" + result)

  new_description = split_result[0]
  cl_files_text = split_result[1]
  if new_description != description:
    change_info.description = new_description
    if change_info.issue:
      # Update the Rietveld issue with the new description.
      change_info.UpdateRietveldDescription()

  new_cl_files = []
  for line in cl_files_text.splitlines():
    if not len(line):
      continue
    if line.startswith("---"):
      break
    status = line[:7]
    file = line[7:]
    new_cl_files.append((status, file))
  change_info.files = new_cl_files

  change_info.Save()
  print change_info.name + " changelist saved."
  if change_info.MissingTests():
    Warn("WARNING: " + MISSING_TEST_MSG)

# We don't lint files in these path prefixes.
IGNORE_PATHS = ("webkit",)

# Valid extensions for files we want to lint.
CPP_EXTENSIONS = ("cpp", "cc", "h")

def Lint(change_info, args):
  """Runs cpplint.py on all the files in |change_info|"""
  try:
    import cpplint
  except ImportError:
    ErrorExit("You need to install cpplint.py to lint C++ files.")

  # Change the current working directory before calling lint so that it
  # shows the correct base.
  previous_cwd = os.getcwd()
  os.chdir(GetRepositoryRoot())

  # Process cpplints arguments if any.
  filenames = cpplint.ParseArguments(args + change_info.FileList())

  for file in filenames:
    if len([file for suffix in CPP_EXTENSIONS if file.endswith(suffix)]):
      if len([file for prefix in IGNORE_PATHS if file.startswith(prefix)]):
        print "Ignoring non-Google styled file %s" % file
      else:
        cpplint.ProcessFile(file, cpplint._cpplint_state.verbose_level)

  print "Total errors found: %d\n" % cpplint._cpplint_state.error_count
  os.chdir(previous_cwd)


def DoPresubmitChecks(change_info, committing):
  """Imports presubmit, then calls presubmit.DoPresubmitChecks."""
  # TODO(termie): we don't have presubmit checks, so we don't do any yet
  #               but it'd be great to add some
  return True

  # Need to import here to avoid circular dependency.
  import presubmit
  result = presubmit.DoPresubmitChecks(change_info,
                                       committing,
                                       verbose=False,
                                       output_stream=sys.stdout,
                                       input_stream=sys.stdin)
  if not result:
    print "\nPresubmit errors, can't continue (use --no_presubmit to bypass)"
  return result


def Changes():
  """Print all the changelists and their files."""
  for cl in GetCLs():
    change_info = LoadChangelistInfo(cl, True, True)
    print "\n--- Changelist " + change_info.name + ":"
    for file in change_info.files:
      print "".join(file)


def main(argv=None):
  if argv is None:
    argv = sys.argv

  if len(argv) == 1:
    Help()
    return 0;

  # Create the directory where we store information about changelists if it
  # doesn't exist.
  if not os.path.exists(GetInfoDir()):
    os.mkdir(GetInfoDir())

  # Commands that don't require an argument.
  command = argv[1]
  if command == "opened":
    Opened()
    return 0
  if command == "status":
    Opened()
    print "\n--- Not in any changelist:"
    UnknownFiles([])
    return 0
  if command == "nothave":
    UnknownFiles(argv[2:])
    return 0
  if command == "changes":
    Changes()
    return 0
  if command == "help":
    Help(argv[2:])
    return 0
  if command == "diff" and len(argv) == 2:
    files = GetFilesNotInCL()
    print GenerateDiff([x[1] for x in files])
    return 0
  if command == "settings":
    ignore = GetCodeReviewSetting("UNKNOWN");
    print CODEREVIEW_SETTINGS
    return 0

  if len(argv) == 2:
    if command == "change":
      # Generate a random changelist name.
      changename = GenerateChangeName()
    else:
      ErrorExit("Need a changelist name.")
  else:
    changename = argv[2]

  # When the command is 'try' and --patchset is used, the patch to try
  # is on the Rietveld server. 'change' creates a change so it's fine if the
  # change didn't exist. All other commands require an existing change.
  fail_on_not_found = command != "try" and command != "change"
  if command == "try" and changename.find(',') != -1:
    change_info = LoadChangelistInfoForMultiple(changename, True, True)
  else:
    change_info = LoadChangelistInfo(changename, fail_on_not_found, True)

  if command == "change":
    Change(change_info)
  elif command == "lint":
    Lint(change_info, argv[3:])
  elif command == "upload":
    UploadCL(change_info, argv[3:])
  elif command == "presubmit":
    PresubmitCL(change_info)
  elif command in ("commit", "submit"):
    Commit(change_info, argv[3:])
  elif command == "delete":
    change_info.Delete()
  elif command == "try":
    # When the change contains no file, send the "changename" positional
    # argument to trychange.py.
    if change_info.files:
      args = argv[3:]
    else:
      change_info = None
      args = argv[2:]
    TryChange(change_info, args)
  else:
    # Everything else that is passed into gcl we redirect to svn, after adding
    # the files. This allows commands such as 'gcl diff xxx' to work.
    args =["svn", command]
    root = GetRepositoryRoot()
    args.extend([os.path.join(root, x) for x in change_info.FileList()])
    if command == "diff":
      moved_files = change_info.GetMoved(root=root)
      for f in moved_files:
        args.remove(f)
        print DiffPrint(f)
    RunShell(args, True)
  return 0


if __name__ == "__main__":
  sys.exit(main())
