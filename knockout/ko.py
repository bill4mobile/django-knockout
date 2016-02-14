import cgi
import json
import datetime

from django.template.loader import render_to_string
from django.db.models.fields import related, files
from django.utils.safestring import mark_safe


class KnockoutModel():

    def __init__(
        self, model,
        field_name=None,
        follow_fks=True, follow_m2ms=True,
        follow_reverse_fks=True
            ):
        self.field_name = field_name
        self.model = model
        self.follow_fks = follow_fks
        self.follow_m2ms = follow_m2ms
        self.follow_reverse_fks = follow_reverse_fks

        self._get_fields(model, follow_fks, follow_m2ms, follow_reverse_fks)

    def _get_knockout_fields(self, model):
        knockout_fields = model.knockout_fields()
        fields = []
        for knockout_field in knockout_fields:
            fields.append(model._meta.get_field(knockout_field))

        return fields

    def _get_relation(self, field):
        model = field.rel.to
        knockout_model = KnockoutModel(model, field_name=field.name)

        return knockout_model

    def _get_reverse_relation(self, field):
        model = field.related_model
        knockout_model = KnockoutModel(
            model,
            field_name=field.name,
            follow_fks=False,
            follow_m2ms=False,
            follow_reverse_fks=False
        )

        return knockout_model

    def _get_fields(
        self, model, follow_fks=True, follow_m2ms=True, follow_reverse_fks=True
            ):
        if hasattr(model, 'knockout_fields'):
            model_fields = self._get_knockout_fields(model)
        else:
            model_fields = model._meta.get_fields()

        fields = []
        fks = []  # Foreign Keys
        m2ms = []  # Many to Manys
        reverse_fks = []  # Many to One / reverse Foreign Key
        for field in model_fields:
            if follow_fks and isinstance(field, related.ForeignKey):
                knockout_model = self._get_relation(field)
                fks.append(knockout_model)
            elif follow_m2ms and isinstance(field, related.ManyToManyField):
                knockout_model = self._get_relation(field)
                m2ms.append(knockout_model)
            elif (
                  follow_reverse_fks and
                  isinstance(field, related.ManyToOneRel)
                    ):
                # TODO: is this worth it? is this correct?
                knockout_model = self._get_reverse_relation(field)
                reverse_fks.append(knockout_model)
            elif isinstance(field, related.ManyToManyRel):
                continue
            else:
                fields.append(field.name)

        self.fields = fields
        self.fks = fks
        self.m2ms = m2ms
        self.reverse_fks = reverse_fks


def ko_list(model):
    if hasattr(model, "comparator"):
        comparator = str(model.comparator())
    else:
        comparator = 'id'

    model_name = model.__name__
    model_arg = model_name.lower()
    model_args = model_name.lower() + "s"

    list_string = render_to_string(
        "knockout/list.js",
        {
            'model_name': model_name,
            'comparator': comparator,
            'model_arg': model_arg,
            'model_args': model_args,
        }
    )

    return list_string


def ko_model(model, knockout_model=None, models=None):
    if not knockout_model:
        knockout_model = KnockoutModel(model)
    fields = knockout_model.fields
    fk_knockout_models = knockout_model.fks
    m2m_knockout_models = knockout_model.m2ms
    reverse_fk_knockout_models = knockout_model.reverse_fks

    model_name = model.__name__
    model_arg = model_name.lower()
    model_args = model_name.lower() + "s"

    if not models:
        # Only define a knockout view model for a django model once
        models = []

    for fk_knockout_model in fk_knockout_models:
        fk_model = fk_knockout_model.model
        fk_knockout_model.model_name = fk_model.__name__
        if fk_model.__name__ not in models:
            fk_knockout_model.model_string = ko_model(
                fk_model, fk_knockout_model, models
            )
            models.append(fk_model.__name__)

    for m2m_knockout_model in m2m_knockout_models:
        m2m_model = m2m_knockout_model.model
        m2m_knockout_model.model_list = ko_list(m2m_model)
        if m2m_model.__name__ not in models:
            m2m_knockout_model.model_string = ko_model(
                m2m_model, m2m_knockout_model, models
            )
            models.append(m2m_model.__name__)

    for reverse_fk_knockout_model in reverse_fk_knockout_models:
        fk_model = reverse_fk_knockout_model.model
        reverse_fk_knockout_model.model_name = fk_model.__name__
        if fk_model.__name__ not in models:
            reverse_fk_knockout_model.model_string = ko_model(
                fk_model, reverse_fk_knockout_model, models
            )
            models.append(fk_model.__name__)

    model_string = render_to_string(
        "knockout/model.js",
        {
            'model_name': model_name,
            'model_arg': model_arg,
            'model_args': model_args,
            'fields': fields,
            'fk_knockout_models': fk_knockout_models,
            'm2m_knockout_models': m2m_knockout_models,
            'reverse_fk_knockout_models': reverse_fk_knockout_models,
        }
    )

    return model_string


def ko_view_model(
    model,
    knockout_model=None,
    follow_fks=False,
    follow_m2ms=False,
    follow_reverse_fks=False
        ):
    if not knockout_model:
        knockout_model = KnockoutModel(
            model, None, follow_fks, follow_m2ms, follow_reverse_fks
        )

    model_name = model.__name__
    view_model_string = model_name + "ViewModel"

    model_list_string = ko_list(model)
    model_string = ko_model(model, knockout_model)

    view_model_string = render_to_string(
        "knockout/view_model.js",
        {
            'view_model_string': view_model_string,
            'model_list_string': model_list_string,
            'model_string': model_string,
        }
    )

    return view_model_string


def ko_bindings(model, element_id=None, data_variable=None, ignore_data=False):
    model_name = model.__name__
    view_model_string = model_name + "ViewModel"
    if data_variable:
        model_data_string = data_variable
    else:
        model_data_string = model_name + "Data"

    model_bindings_string = render_to_string(
        "knockout/bindings.js",
        {
            'view_model_string': view_model_string,
            'model_data_string': model_data_string,
            'element_id': element_id,
            'ignore_data': ignore_data,
        }
    )

    return model_bindings_string


def _model_data(obj, fields, safe):
    obj_dict = {}
    for field in fields:
        if hasattr(obj, field):
            attribute = getattr(obj, field)
            if not safe and isinstance(attribute, str):
                attribute = cgi.escape(attribute)
            elif isinstance(attribute, files.FieldFile):
                if hasattr(attribute, 'url'):
                    attribute = attribute.url
            obj_dict[field] = attribute
        # TODO: this would create recursion
        # elif hasattr(obj, field + '_set'):
        #     attribute = getattr(obj, field + '_set')
        else:
            obj_dict[field] = None

    return obj_dict


def _model_foreign_key_data(obj, knockout_models, safe):
    foreign_key_dict = {}
    for knockout_model in knockout_models:
        field_name = knockout_model.field_name

        if hasattr(obj, field_name):
            fk_obj = getattr(obj, field_name)
        else:
            fk_obj = None

        all_dict = {}
        if knockout_model.fields:
            foreign_key_obj_dict = _model_data(
                fk_obj, knockout_model.fields, safe
            )
            all_dict.update(foreign_key_obj_dict)

        if knockout_model.fks:
            nested_foreign_key_obj_dict = _model_foreign_key_data(
                fk_obj, knockout_model.fks, safe
            )
            all_dict.update(nested_foreign_key_obj_dict)

        if knockout_model.m2ms:
            nested_many_to_many_obj_dict = _model_many_to_many_data(
                fk_obj, knockout_model.m2ms, safe
            )
            all_dict.update(nested_many_to_many_obj_dict)

        if knockout_model.reverse_fks:
            nested_reverse_foreign_key_obj_dict = \
                _model_reverse_foreign_key_data(
                    fk_obj, knockout_model.reverse_fks, safe
                )
            all_dict.update(nested_reverse_foreign_key_obj_dict)

        foreign_key_dict[field_name] = all_dict

    return foreign_key_dict


def _model_many_to_many_data(obj, knockout_models, safe):
    many_to_many_dict = {}
    for knockout_model in knockout_models:
        field_name = knockout_model.field_name

        if hasattr(obj, field_name):
            m2m_list = getattr(obj, field_name).all()
        else:
            m2m_list = []

        many_to_many_obj_list = []
        for m2m_obj in m2m_list:
            all_dict = {}

            if knockout_model.fields:
                many_to_many_obj_dict = _model_data(
                    m2m_obj, knockout_model.fields, safe
                )
                all_dict.update(many_to_many_obj_dict)

            if knockout_model.fks:
                nested_foreign_key_obj_dict = _model_foreign_key_data(
                    m2m_obj, knockout_model.fks, safe
                )
                all_dict.update(nested_foreign_key_obj_dict)

            if knockout_model.m2ms:
                nested_many_to_many_obj_dict = _model_many_to_many_data(
                    m2m_obj, knockout_model.m2ms, safe
                )
                all_dict.update(nested_many_to_many_obj_dict)

            if knockout_model.reverse_fks:
                nested_reverse_foreign_key_obj_dict = \
                    _model_reverse_foreign_key_data(
                        m2m_obj, knockout_model.reverse_fks, safe
                    )
                all_dict.update(nested_reverse_foreign_key_obj_dict)

            many_to_many_obj_list.append(all_dict)

        many_to_many_dict[field_name] = many_to_many_obj_list

    return many_to_many_dict


def _model_reverse_foreign_key_data(obj, knockout_models, safe):
    reverse_foreign_key_dict = {}
    for knockout_model in knockout_models:
        field_name = knockout_model.field_name

        # TODO: handle related_name being set
        field_name_set = field_name + '_set'
        if hasattr(obj, field_name_set):
            reverse_fk_list = getattr(obj, field_name_set).all()
        else:
            reverse_fk_list = []

        reverse_foreign_key_obj_list = []
        for reverse_fk_obj in reverse_fk_list:
            all_dict = {}

            if knockout_model.fields:
                many_to_many_obj_dict = _model_data(
                    reverse_fk_obj, knockout_model.fields, safe
                )
                all_dict.update(many_to_many_obj_dict)

            if knockout_model.fks:
                nested_foreign_key_obj_dict = _model_foreign_key_data(
                    reverse_fk_obj, knockout_model.fks, safe
                )
                all_dict.update(nested_foreign_key_obj_dict)

            if knockout_model.m2ms:
                nested_many_to_many_obj_dict = _model_many_to_many_data(
                    reverse_fk_obj, knockout_model.m2ms, safe
                )
                all_dict.update(nested_many_to_many_obj_dict)

            if knockout_model.reverse_fks:
                nested_reverse_foreign_key_obj_dict = \
                    _model_reverse_foreign_key_data(
                        reverse_fk_obj, knockout_model.reverse_fks, safe
                    )
                all_dict.update(nested_reverse_foreign_key_obj_dict)

            reverse_foreign_key_obj_list.append(all_dict)

        reverse_foreign_key_dict[field_name] = reverse_foreign_key_obj_list

    return reverse_foreign_key_dict


def ko_data(
    model, queryset, knockout_model=None, data_variable=None, safe=False
        ):
    if not knockout_model:
        knockout_model = KnockoutModel(model)
    fields = knockout_model.fields
    fk_knockout_models = knockout_model.fks
    m2m_knockout_models = knockout_model.m2ms
    reverse_fk_knockout_models = knockout_model.reverse_fks

    model_data = []
    for obj in queryset:
        all_dict = {}

        obj_dict = _model_data(obj, fields, safe)
        all_dict.update(obj_dict)

        foreign_key_dict = _model_foreign_key_data(
            obj, fk_knockout_models, safe
        )
        all_dict.update(foreign_key_dict)

        many_to_many_dict = _model_many_to_many_data(
            obj, m2m_knockout_models, safe
        )
        all_dict.update(many_to_many_dict)

        reverse_foreign_key_dict = \
            _model_reverse_foreign_key_data(
                obj, reverse_fk_knockout_models, safe
            )
        all_dict.update(reverse_foreign_key_dict)

        model_data.append(all_dict)

    model_name = model.__name__
    if data_variable:
        model_data_string = data_variable
    else:
        model_data_string = model_name + "Data"
    model_args = model_name.lower() + "s"

    dthandler = (
        lambda obj:
            obj.isoformat()
            if isinstance(obj, (datetime.datetime, datetime.date))
            else None
    )

    json_data = json.dumps({model_args: model_data}, default=dthandler)

    model_data_string = render_to_string(
        'knockout/data.js',
        {
            'model_data_string': model_data_string,
            'data': json_data,
        }
    )

    return model_data_string


def ko(model, queryset, knockout_model=None):
    if not knockout_model:
        knockout_model = KnockoutModel(model)

    ko_data_string = (
        ko_data(model, queryset, knockout_model)
        if queryset else mark_safe("")
    )

    ko_view_model_string = ko_view_model(model, knockout_model)
    ko_bindings_string = ko_bindings(model)

    ko_string = ko_data_string + ko_view_model_string + ko_bindings_string

    return ko_string
