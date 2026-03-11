from __future__ import annotations

"""Repository abstractions and mock implementations for API services."""

from dataclasses import dataclass
from typing import List, Optional, Protocol

from property_advisor.api.db import DatabaseSessionFactory
from property_advisor.api.mock_fixtures import (
    COMPARABLES_FIXTURE,
    PROPERTY_ADVISOR_FIXTURE,
    SUBURBS_OVERVIEW_FIXTURE,
)
from property_advisor.api.schemas import (
    ComparableItem,
    ComparablesResponse,
    PropertyAdvisorResponse,
    SuburbOverviewItem,
)


class SuburbRepository(Protocol):
    def list_overview(self) -> List[SuburbOverviewItem]:
        ...

    def get_by_slug(self, slug: str) -> Optional[SuburbOverviewItem]:
        ...


class PropertyAdviceRepository(Protocol):
    def get_by_address_or_slug(self, query: str) -> Optional[PropertyAdvisorResponse]:
        ...


class ComparableRepository(Protocol):
    def list_by_subject(self, query: str) -> List[ComparableItem]:
        ...


class MockSuburbRepository:
    def list_overview(self) -> List[SuburbOverviewItem]:
        return list(SUBURBS_OVERVIEW_FIXTURE.items)

    def get_by_slug(self, slug: str) -> Optional[SuburbOverviewItem]:
        return next((item for item in SUBURBS_OVERVIEW_FIXTURE.items if item.slug == slug), None)


class MockPropertyAdviceRepository:
    def get_by_address_or_slug(self, query: str) -> Optional[PropertyAdvisorResponse]:
        normalized = query.strip().lower()
        default = PROPERTY_ADVISOR_FIXTURE
        if not normalized:
            return default

        suburb = normalized.split(",")[-1].strip()
        if "southport" in suburb or normalized == "southport-qld-4215":
            return default

        if normalized == "burleigh-heads-qld-4220" or "burleigh heads" in normalized:
            return default.model_copy(
                update={
                    "property": default.property.model_copy(
                        update={"address": "42 Ocean View Drive, Burleigh Heads QLD 4220", "beds": 3}
                    ),
                    "advice": default.advice.model_copy(
                        update={
                            "recommendation": "consider",
                            "confidence": "medium",
                            "headline": "Comparable spread is tighter and days-on-market signal is healthier.",
                        }
                    ),
                }
            )

        return None


class MockComparableRepository:
    def list_by_subject(self, query: str) -> List[ComparableItem]:
        normalized = query.strip().lower()
        if not normalized:
            return list(COMPARABLES_FIXTURE.items)

        filtered = [item for item in COMPARABLES_FIXTURE.items if normalized in item.address.lower()]
        return filtered if filtered else list(COMPARABLES_FIXTURE.items)


class PostgresSuburbRepository(MockSuburbRepository):
    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory


class PostgresPropertyAdviceRepository(MockPropertyAdviceRepository):
    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory


class PostgresComparableRepository(MockComparableRepository):
    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory


@dataclass(frozen=True)
class RepositoryContainer:
    suburbs: SuburbRepository
    property_advice: PropertyAdviceRepository
    comparables: ComparableRepository


def create_repository_container(session_factory: DatabaseSessionFactory) -> RepositoryContainer:
    if session_factory.is_configured():
        return RepositoryContainer(
            suburbs=PostgresSuburbRepository(session_factory),
            property_advice=PostgresPropertyAdviceRepository(session_factory),
            comparables=PostgresComparableRepository(session_factory),
        )

    return RepositoryContainer(
        suburbs=MockSuburbRepository(),
        property_advice=MockPropertyAdviceRepository(),
        comparables=MockComparableRepository(),
    )
