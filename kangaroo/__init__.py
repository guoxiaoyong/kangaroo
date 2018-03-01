# Author: Guo Xiaoyong
# Date: 2018-03-01

import absl.flags as flags

flags.DEFINE_boolean(
    "save_ics",
    False,
    "Save the downloaded ics file."
)

flags.DEFINE_string(
    "dryrun",
    False,
    "Print out actions that will be taken in no dryrun mode without "\
    "actually carrying out the actions."
)
