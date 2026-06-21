from django import template

register = template.Library()


@register.filter
def aria_field(bound_field):
    '''Render a form field widget with accessibility attributes wired in.

    Adds ``aria-invalid`` when the field has errors and ``aria-describedby``
    pointing to the hint/error containers rendered by the shared
    ``accounts/partials/form_fields.html`` partial. Keeps templates free of
    per-widget attribute plumbing while ensuring screen readers announce
    validation state.
    '''
    attrs = {}
    described_by = []
    field_id = bound_field.id_for_label

    if bound_field.help_text:
        described_by.append('hint_{0}'.format(field_id))
    if bound_field.errors:
        described_by.append('error_{0}'.format(field_id))
        attrs['aria-invalid'] = 'true'
    if described_by:
        attrs['aria-describedby'] = ' '.join(described_by)

    return bound_field.as_widget(attrs=attrs)
