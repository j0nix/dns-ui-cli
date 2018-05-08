![Development in progress](https://img.shields.io/badge/Dev%20status-In--Progress-orange.svg)

# dns-ui-cli
cli for dns-ui, https://github.com/operasoftware/dns-ui. Sure, a pretty straightforward GUI but it's still a GUI that you need to click around in. With this cli you don't need to drop your hands from the keaybord and fiddeling around with the mouse. Also, big zones slows down the whole web 2.0 feeling.

## Why?
To make it simple

## Scope?
Common tasks. Add, update and delete A records in a zone.

# Help
## Workflow
1. select zone
2. add,update or delete records
3. commit your changes

## how
First you login to to the cli, when you do that it fetches all zones your user are allowed to edit. 
- **Then you select a zone to work in** (here you can TAB to list your options)
  ```
  [ZONE ?]: zone my.company.se. 
  using zone my.company.se.
  ```
- **Time to add, update or delete records**
  ```
  [ZONE my.company.se.]: add server-1 10.10.10.10
  Added server-1 10.10.10.10 to commit queue
  [ZONE my.company.se.]: add server-2 10.10.10.11
  Added server-2 10.10.10.11 to commit queue
  [ZONE my.company.se.]: add server-3 10.10.10.12
  Added server-3 10.10.10.12 to commit queue
  ```
- **To make sure you got it all list whatever is in your commit queue**
  ```
  [ZONE my.company.se.]: list
  [0] add server-1 10.10.10.10
  [1] add server-2 10.10.10.11
  [2] add server-3 10.10.10.12
  ```
- **ohh... we don't need to add that record with index 2, lets remove it from queue**
  ```
  [ZONE my.company.se.]: remove 2
  Removed index 2 from commit queue
  [ZONE my.company.se.]: list
  [0] add server-1 10.10.10.10
  [1] add server-2 10.10.10.11
  ```
- **Time to commit your queue to make your changes live**
  ```
  [ZONE my.company.se.]: commit my-commit-comment
  SUCCESS adding to my.company.se.
  ```
  
- Get help
  ```
  [ZONE ?]: help

  Documented commands (type help <topic>):
  ========================================
  EOF  add  commit  delete  exit  help  list  remove  update  zone
  ```
## Config file

To override default url to API you need to create yaml file called **.dns-ui-cli.yml** in you home directory.

* Override either **url** or **api** endpoint

```
dns-ui:
  url: https://mydnsui.mydomain.com
  api: /api/v2/zones/

```
Also can also enable verifying the SSL certficate (default False)

```
dns-ui:
  ssl-verify: True

```

## TODO

- Add more help data
- Catch more exceptions
- Add support for CNAME
- Add debug option (To track down those inglorious typeo:s)
- Add support to add username & password (encrypted as hell) in config file

