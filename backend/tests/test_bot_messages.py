import inspect

from app.bot import messages
from app.models import ProjectStatus
from app.services import errors


def domain_error_classes():
    return [
        cls
        for _, cls in inspect.getmembers(errors, inspect.isclass)
        if issubclass(cls, errors.DomainError) and cls is not errors.DomainError
    ]


def test_every_domain_error_has_a_specific_message():
    for cls in domain_error_classes():
        assert messages.error_message(cls(1)) != messages.UNEXPECTED_ERROR, cls.__name__


def test_active_limit_message_names_the_limit():
    assert "3" in messages.error_message(errors.ActiveLimitReached(3))


def test_unknown_exception_gets_the_generic_message():
    assert messages.error_message(ValueError("boom")) == messages.UNEXPECTED_ERROR


def test_every_status_is_translated():
    assert set(messages.STATUS_LABELS) == set(ProjectStatus)
    assert [messages.STATUS_LABELS[s] for s in ProjectStatus] == ["idea", "activo", "pausa", "terminado"]


def test_days_label():
    assert messages.days_label(0) == "tocado hoy"
    assert messages.days_label(1) == "1 día sin tocar"
    assert messages.days_label(5) == "5 días sin tocar"


def test_export_summary_pluralises_and_lists_orphans():
    from app.schemas.export import ExportSummary

    one = ExportSummary(projects_exported=1, files_written=5, files_unchanged=0, orphans=[])
    many = ExportSummary(projects_exported=3, files_written=0, files_unchanged=13, orphans=["a", "b"])

    assert messages.export_summary(one) == "Export listo: 1 proyecto, 5 archivos escritos, 0 sin cambios."
    assert messages.export_summary(many).splitlines() == [
        "Export listo: 3 proyectos, 0 archivos escritos, 13 sin cambios.",
        "Carpetas huérfanas (no se tocaron): a, b",
    ]
