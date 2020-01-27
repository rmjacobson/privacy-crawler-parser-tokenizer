# CMU RELAB: Automated privacy policy annotations

# Virtual Environments
To set up your virtual environment, refer to
[this](https://docs.python-guide.org/dev/virtualenvs/#lower-level-virtualenv)
documentation.


To download all dependencies:
```
$ pip install -r requirements.txt
```


If you've downloaded any additional libraries, log those libraries to your
requirements.txt file by running the following:
```
$ pip freeze -l > requirements.txt
```

# Environment Notes
MacOS Catilina (10.15) and above have limited the user's default ability
to multithread.  If running these versions of the OS, need to add the
following line to ~/.bash_profile and reload the shell.
```
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```
Source: https://stackoverflow.com/questions/50168647/multiprocessing-causes-python-to-crash-and-gives-an-error-may-have-been-in-progr
