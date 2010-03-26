{
{% for i in pathtag %}
 '{{i}}'{% if not forloop.last %},{% endif %}
{% endfor %}
}
