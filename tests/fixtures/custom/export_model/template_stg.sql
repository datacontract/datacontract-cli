
select
{%- for field in schema.properties %}
  try_cast({{ field.name }} as {{ field.physicalType | lower }}) as {{ field.name }}
{%- endfor %}
from {{ "{{" }} source('{{ data_contract.id.split(':')[-1] }}', '{{ schema_name }}') {{ "}}" }}
