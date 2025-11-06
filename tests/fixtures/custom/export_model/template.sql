
SELECT
{%- for field_name, field in model.fields.items() %}
  {%- if field.type == "timestamp" %}
  DATETIME({{ field_name }}, "Asia/Tokyo") AS {{ field_name }},
  {%- else %}
  {{ field_name }} AS {{ field_name }},
  {%- endif %}
{%- endfor %}
FROM {{ "{{" }} ref('{{ model_name }}') {{ "}}" }}