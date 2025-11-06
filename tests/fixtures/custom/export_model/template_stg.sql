
select
{%- for field_name, field in model.fields.items() %}
  try_cast({{ field_name }} as {{ field.type | lower }}) as {{ field_name }}
{%- endfor %}
from {{ "{{" }} source('{{ data_contract.id.split(':')[-1] }}', '{{ model_name }}') {{ "}}" }}
