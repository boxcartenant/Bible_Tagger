# How to Create Migration Scripts

### Naming

Naming should always have this format ```#-to-#.py``` where the first # is the db USER_VERSION that can be migrated from, and the second # is the db USER_VERSION that can be migrated to.

### Arguments

Migration scripts MUST have a function migrate_database(old_db_path, create_backup=True)

### Behavior

Migration scripts should always create a backup of the db file, called <oldname>_backup.dbd, unless explicitly told not to.
Then it should migrate the data. Do not try to keep old structures. The old structures are in the backup file if requested.
Make sure to update USER_VERSION
DO NOT create scripts that migrate dbs more than one version up. Bible Tagger Migration automatically chains migration scripts to bring any db to the current version
