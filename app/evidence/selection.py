from __future__ import annotations

from collections.abc import Sequence


def source_diverse_indexes(
    source_types: Sequence[str],
    required_sources: Sequence[str],
) -> tuple[int, ...]:
    selected: list[int] = []
    for required_source in required_sources:
        index = next(
            (
                position
                for position, source_type in enumerate(source_types)
                if (
                    position not in selected
                    and source_type == required_source
                )
            ),
            None,
        )
        if index is not None:
            selected.append(index)
    selected.extend(
        index
        for index in range(len(source_types))
        if index not in selected
    )
    return tuple(selected)


__all__ = ["source_diverse_indexes"]
