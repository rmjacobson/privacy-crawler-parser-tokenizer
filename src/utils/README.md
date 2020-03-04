# Utilities Module

This module contains support code that is either used in many places
in other modules/top-level scripts, or that which is so general it
could be used in multiple modules/top-level scripts.  Mostly this is
functionality like print progress bars, making/cleaning directories for
new output, or making web requests, but it may be added to at a later
date.

Note: unlike other modules in this project, code in the utils module
is not meant to be run, only imported into other modules/scripts.