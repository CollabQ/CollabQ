=========================
CollabQ Community Edition
=========================

Getting the code
----------------

You can download the latest released version of CollabQ from:

Join Community for Support. To check out the lastest code from the CollabQ GIT Repository, use these Public Clone URLs :

Github URL: http://github.com/CollabQ/CollabQ/tree/master
Github download: http://github.com/CollabQ/CollabQ/tarball/master
Public Clone URL: git://github.com/CollabQ/CollabQ.git

Dependencies
------------
  
  * Python 2.4 or 2.5
  * docutils: http://docutils.sourceforge.net/

Quickstart
==========
To get a development version running:

# Install Python 2.5 or above on your local system.
# Download the CollabQ zipfile from http://ww.collabq.com/
# Unzip it to C://CollabQ
# Go to C://CollabQ and start runserver.bat from the explore window. This will start CollabQ in a new command window
# In the command window, look for "INFO:root:Running application collabq on port 8080: http://localhost:8080"
# Start a browser and load http://localhost:8080 and you will see CollabQ welcome page

Deploying to Google App Engine
==============================================
Configure your app
------------------
Get an Google App ID and add it to the file app.yaml in c://project/mycollabsite. For example if your app_id is mycollabqsite your app.yaml should start similar to:

  application: mycollabqsite
  version: 1
  runtime: python
  ...

Edit the setting.py file and change the variable APP_ID to your app_id. If your app_id is mycollabqsite your app.yaml should start similar to:

  ...
  APP_ID = 'mycollabqsite'
  ...

Upload your App
---------------
Open a command line and go to your PROJECT_PATH. For example if you are on Windows and your project is under c://CollabQ you should type:

  c:
  cd c://CollabQ

To upload your app to GAE type:

  python manage.py update

If this does not work, try:

  c:\Python26\python manage.py update

It will prepare the files and will ask you your email and your password to verify if you have access to the app, you should enter the email and your password which you used to create your GAE App:

  ...
  Scanned 14500 files.
  Scanned 15000 files.
  Scanned 15500 files.
  Initiating update.
  Email:

Installing
==========
After the app is uploaded, you have to fill the installation form in your GAE app. Visit your app URL, it has the following format: app_id.appspot.com. The Site will ask you the following fields:

* Site Name (Required) - What name will you want for your site.
* Tagline (Optional).
* Root User Mail (Required) - The email for the Admin User.
* Root User Password - The password for the Admin User
* Default Channel (Required) - The channel name by the default channel, every registered user will be part of this channel.
* Post Name (Required) - The colloquial name for an entry, mostly used for branding purposes 