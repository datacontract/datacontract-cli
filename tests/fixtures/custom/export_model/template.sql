
SELECT
{%- for field in schema.properties %}
  {%- if field.physicalType == "timestamp" %}
  DATETIME({{ field.name }}, "Asia/Tokyo") AS {{ field.name }},
  {%- else %}
  {{ field.name }} AS {{ field.name }},
  {%- endif %}
{%- endfor %}
FROM {{ "{{" }} ref('{{ schema_name }}') {{ "}}" }}
