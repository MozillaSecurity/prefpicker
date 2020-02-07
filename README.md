PrefPicker
==========

Manage & generate prefs.js files

YAML Template Structure
-----------------------

This document is made up of variants, prefs and values.

`pref` is the name of the preference that will be added to the prefs.js file. This is an unquoted string.
Valid prefs can be found in [all.js](https://hg.mozilla.org/mozilla-central/file/tip/modules/libpref/init/all.js) or in [StaticPrefList.yml](https://hg.mozilla.org/mozilla-central/file/tip/modules/libpref/init/StaticPrefList.yaml).

`value` can be a bool, int, string or null. Adding multiple potential values is possible.
When multiple values are present one is chosen at random when generating the output.
Using a value of null will skip adding the pref to the output prefs.js file.

`variant` is a subset of values to be used in place of the default values.
The default variant is used unless a variant is specified.

There are a few mechanisms in place to help keep the file in order:
- All prefs must have a default variant
- All variants be defined in the `variant` list.
- All variants in the variant list must be used
- All variants must be a list and contain values.

```yml
# example.yml
variant:      # list for extra variants, default is implied
 - alt        # name of extra variant
pref:
 pref.name:   # unquoted name of the pref used in prefs.js
   default:   # variant definition, default is required
     - 0      # potential value
   alt:       # extra optional variant
     - 1      # if multiple values are defined one is chosen randomly
     - null   # null is a special case meaning do not add the pref
```
