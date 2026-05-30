from geaiq_mdp.enums import SourceType


def source_type_todo_error(source, *_args, **_kwargs):
    valid_source_types = {st.value for st in SourceType} - {'TODO'}
    return [
        {
            "type": "error",
            "message": f"Source type not defined for {source.slug}",
            "details": [
                f"Please set up the source type diferent to TODO to allow it to be processed.",
                f"Options: {valid_source_types}"
            ],
        }
    ]
