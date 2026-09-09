"""The field that identifies one element of an ODCS list.

Read by the Excel workbook to address an element from a child sheet. Paths are ODCS field paths,
without list indices; a list with no natural key (quality, relationships, verified statements,
constraints) is addressed by its `id` instead.
"""

NATURAL_KEYS = {
    "schema": "name",
    "schema.properties": "name",  # recursive, dotted path in the workbook
    "slaProperties": "property",
    "servers": "server",
    "support": "channel",
    "roles": "role",
    "team.members": "username",
    "enum": "value",
    "synonyms": "synonym",
}
