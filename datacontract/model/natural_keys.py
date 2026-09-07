"""The field that identifies one element of an ODCS list.

Read by the changelog (to diff lists by key instead of position) and by the Excel workbook
(to address an element from a child sheet). Paths are ODCS field paths, without list indices.
"""

NATURAL_KEYS = {
    "schema": "name",
    "schema.properties": "name",  # recursive, dotted path in the workbook
    "slaProperties": "property",
    "servers": "server",
    "servers.roles": "role",
    "support": "channel",
    "roles": "role",
    "team.members": "username",
    "customProperties": "property",
    "authoritativeDefinitions": "url",
    "enum": "value",
    "synonyms": "synonym",
    "relationships": "id",  # the changelog falls back to from:to
    "verifiedStatements": "question",  # the workbook requires an id instead
    "constraints": "constraint",  # the workbook requires an id instead
    "quality": "name",  # the workbook requires an id instead
}
