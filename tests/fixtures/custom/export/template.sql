{%- for schema in data_contract.schema_ %}
{#- Export only the first schema #}
{%- if loop.first -%}
SELECT
{%- for prop in schema.properties %}
  {%- if prop.logicalType == "timestamp" or prop.physicalType == "timestamp" %}
  DATETIME({{ prop.name }}, "Asia/Tokyo") AS {{ prop.name }},
  {%- else %}
  {{ prop.name }} AS {{ prop.name }},
  {%- endif %}
{%- endfor %}
FROM
  {{ "{{" }} ref('{{ schema.name }}') {{ "}}" }}
{%- endif %}
{%- endfor %}

