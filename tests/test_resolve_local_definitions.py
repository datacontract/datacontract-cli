"""Tests for resolving `authoritativeDefinitions` that point at a file on disk,
either as `<contract>#<fragment>` or as a bare `<file>` that is the definition.

The contract under test: a technical contract can link each of its properties
to the business attribute that carries the meaning — a property in a sibling
contract, or a file holding that one definition — the CLI resolves that link
relative to the referencing file, and a broken or circular reference rejects
the contract rather than passing silently.
"""

from pathlib import Path
from textwrap import dedent

import pytest
import responses
from open_data_contract_standard.model import (
    AuthoritativeDefinition,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
)

from datacontract.lint import resolve
from datacontract.lint.resolve import (
    clear_definition_cache,
    inline_definitions_into_data_contract,
    resolve_data_contract,
)
from datacontract.model.exceptions import DataContractException

EXAMPLES = Path(__file__).parent.parent / "examples" / "business-definitions"


@pytest.fixture(autouse=True)
def _isolated_cache():
    """The resolver caches parsed files across the process; clear it before each
    test so cases that reuse file paths don't see each other."""
    clear_definition_cache()
    yield
    clear_definition_cache()


def _write(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text(dedent(body).lstrip())
    return path


def _business_contract(directory: Path, name: str = "business.odcs.yaml") -> Path:
    """The contract that owns the business meaning."""
    return _write(
        directory,
        name,
        """
        apiVersion: v3.1.0
        kind: DataContract
        id: business
        version: 1.0.0
        status: active
        schema:
          - name: Top Artists by Year
            id: top_artists_by_year_ba
            properties:
              - name: Artist Name
                id: artist_name
                businessName: Artist Name
                description: The artist name.
                examples:
                  - Lola Young
              - name: address
                properties:
                  - name: City
                    id: city
                    description: The city.
              - name: tags
                logicalType: array
                items:
                  name: tag
                  description: A tag.
        """,
    )


def _referencing_contract(directory: Path, url: str, **inline: str) -> Path:
    """A technical contract with one property linking to `url`. Keyword
    arguments become fields the contract author wrote inline on that property."""
    author_fields = "".join(f"        {field}: {value}\n" for field, value in inline.items())
    return _write(
        directory,
        "technical.odcs.yaml",
        "apiVersion: v3.1.0\n"
        "kind: DataContract\n"
        "id: technical\n"
        "version: 1.0.0\n"
        "status: active\n"
        "schema:\n"
        "  - name: mv_top_artists\n"
        "    properties:\n"
        "      - name: artist_name\n"
        "        logicalType: string\n"
        f"{author_fields}"
        "        authoritativeDefinitions:\n"
        "          - type: businessDefinition\n"
        f"            url: {url}\n",
    )


def _first_property(contract: OpenDataContractStandard) -> SchemaProperty:
    return contract.schema_[0].properties[0]


# --- Resolving against a sibling file ------------------------------------


def test_property_is_resolved_by_id(tmp_path):
    """The fragment addresses the business attribute by its stable `id`, which
    is what makes the reference survive a rename of `name`."""
    _business_contract(tmp_path)
    path = _referencing_contract(tmp_path, "business.odcs.yaml#schema/top_artists_by_year_ba/properties/artist_name")

    prop = _first_property(resolve_data_contract(str(path), inline_references=True))

    assert prop.businessName == "Artist Name"
    assert prop.description == "The artist name."
    assert prop.examples == ["Lola Young"]


def test_property_is_resolved_by_name_when_no_id_matches(tmp_path):
    """`name` is the fallback anchor, so contracts without stable ids can use
    the same syntax."""
    _business_contract(tmp_path)
    path = _referencing_contract(tmp_path, "business.odcs.yaml#schema/Top Artists by Year/properties/Artist Name")

    assert _first_property(resolve_data_contract(str(path), inline_references=True)).businessName == "Artist Name"


def test_nested_property_is_addressable(tmp_path):
    _business_contract(tmp_path)
    path = _referencing_contract(
        tmp_path, "business.odcs.yaml#schema/top_artists_by_year_ba/properties/address/properties/city"
    )

    assert _first_property(resolve_data_contract(str(path), inline_references=True)).description == "The city."


def test_array_items_are_addressable(tmp_path):
    _business_contract(tmp_path)
    path = _referencing_contract(tmp_path, "business.odcs.yaml#schema/top_artists_by_year_ba/properties/tags/items")

    assert _first_property(resolve_data_contract(str(path), inline_references=True)).description == "A tag."


def test_reference_resolves_relative_to_the_referencing_file(tmp_path):
    """The path is relative to the contract that holds the reference, not to the
    working directory -- so a checked-out directory resolves from anywhere."""
    nested = tmp_path / "technical"
    nested.mkdir()
    _business_contract(tmp_path)
    path = _referencing_contract(nested, "../business.odcs.yaml#schema/top_artists_by_year_ba/properties/artist_name")

    assert _first_property(resolve_data_contract(str(path), inline_references=True)).businessName == "Artist Name"


def test_inline_values_win_over_the_referenced_attribute(tmp_path):
    """The technical contract owns its own shape: what it states inline is kept."""
    _business_contract(tmp_path)
    path = _referencing_contract(
        tmp_path,
        "business.odcs.yaml#schema/top_artists_by_year_ba/properties/artist_name",
        description="The artist name as stored in this view.",
    )

    prop = _first_property(resolve_data_contract(str(path), inline_references=True))

    assert prop.description == "The artist name as stored in this view."
    assert prop.businessName == "Artist Name"


def test_identity_fields_are_not_taken_from_the_referenced_attribute(tmp_path):
    """`name`, `id`, and the link itself belong to the referencing contract."""
    _business_contract(tmp_path)
    path = _referencing_contract(tmp_path, "business.odcs.yaml#schema/top_artists_by_year_ba/properties/artist_name")

    prop = _first_property(resolve_data_contract(str(path), inline_references=True))

    assert prop.name == "artist_name"
    assert prop.id is None
    assert [ad.type for ad in prop.authoritativeDefinitions] == ["businessDefinition"]


def test_referenced_file_is_read_once_for_many_properties(tmp_path, monkeypatch):
    """The common case is a whole table pointing at one business object; that
    must not re-read and re-parse the file per property."""
    _business_contract(tmp_path)
    path = _write(
        tmp_path,
        "technical.odcs.yaml",
        """
        apiVersion: v3.1.0
        kind: DataContract
        id: technical
        version: 1.0.0
        status: active
        schema:
          - name: mv_top_artists
            properties:
              - name: artist_name
                authoritativeDefinitions:
                  - type: businessDefinition
                    url: business.odcs.yaml#schema/top_artists_by_year_ba/properties/artist_name
              - name: city
                authoritativeDefinitions:
                  - type: businessDefinition
                    url: business.odcs.yaml#schema/top_artists_by_year_ba/properties/address/properties/city
        """,
    )

    reads: list[str] = []
    original_read_resource = resolve.read_resource

    def counting_read_resource(location: str, config=None) -> str:
        reads.append(location)
        return original_read_resource(location, config)

    monkeypatch.setattr(resolve, "read_resource", counting_read_resource)
    contract = resolve_data_contract(str(path), inline_references=True)

    assert [p.description for p in contract.schema_[0].properties] == ["The artist name.", "The city."]
    assert [r for r in reads if r.endswith("business.odcs.yaml")] == [str(tmp_path / "business.odcs.yaml")]


# --- A file that is the definition itself ---------------------------------


def test_file_without_a_fragment_is_the_definition(tmp_path):
    """No fragment, so there is nothing to address inside the file: the document
    holds the property's elements directly."""
    _write(
        tmp_path,
        "artist_name.odcs.yaml",
        """
        businessName: Artist Name
        description: The artist name.
        examples:
          - Lola Young
        """,
    )
    path = _referencing_contract(tmp_path, "artist_name.odcs.yaml")

    prop = _first_property(resolve_data_contract(str(path), inline_references=True))

    assert prop.businessName == "Artist Name"
    assert prop.description == "The artist name."
    assert prop.examples == ["Lola Young"]
    assert prop.logicalType == "string"  # the referencing contract keeps its own


def test_definition_file_chain_is_resolved_transitively(tmp_path):
    """A definition file may delegate further, to another file or into a
    contract; the referencing contract still ends up with the meaning."""
    _business_contract(tmp_path)
    _write(
        tmp_path,
        "artist_name.odcs.yaml",
        """
        businessName: Artist Name
        authoritativeDefinitions:
          - type: businessDefinition
            url: business.odcs.yaml#schema/top_artists_by_year_ba/properties/artist_name
        """,
    )
    path = _referencing_contract(tmp_path, "artist_name.odcs.yaml")

    prop = _first_property(resolve_data_contract(str(path), inline_references=True))

    assert prop.businessName == "Artist Name"  # the definition file's own value wins
    assert prop.description == "The artist name."  # inherited through the chain
    assert prop.examples == ["Lola Young"]


def test_definition_file_cycle_is_reported(tmp_path):
    """Two definition files referencing each other fail with a cycle error
    rather than recursing until the stack runs out."""
    _write(
        tmp_path,
        "artist_name.odcs.yaml",
        """
        businessName: Artist Name
        authoritativeDefinitions:
          - type: businessDefinition
            url: artist.odcs.yaml
        """,
    )
    _write(
        tmp_path,
        "artist.odcs.yaml",
        """
        description: A performing musician.
        authoritativeDefinitions:
          - type: businessDefinition
            url: artist_name.odcs.yaml
        """,
    )
    path = _referencing_contract(tmp_path, "artist_name.odcs.yaml")

    with pytest.raises(DataContractException) as exc:
        resolve_data_contract(str(path), inline_references=True)
    assert "cycle" in str(exc.value)


def test_missing_definition_file_rejects_the_contract(tmp_path):
    path = _referencing_contract(tmp_path, "missing.odcs.yaml")

    with pytest.raises(DataContractException) as exc:
        resolve_data_contract(str(path), inline_references=True)
    assert "does not exist" in str(exc.value)


def test_contract_file_without_a_fragment_asks_for_a_fragment(tmp_path):
    """A whole contract has no single meaning to inline, so the error says how
    to name the property that was meant."""
    _business_contract(tmp_path)
    path = _referencing_contract(tmp_path, "business.odcs.yaml")

    with pytest.raises(DataContractException) as exc:
        resolve_data_contract(str(path), inline_references=True)
    msg = str(exc.value)
    assert "is a data contract, not a single property" in msg
    assert "#schema/<schema>/properties/<property>" in msg


def test_definition_file_that_is_not_a_property_is_rejected(tmp_path):
    _write(tmp_path, "artist_name.odcs.yaml", "- not: a property\n")
    path = _referencing_contract(tmp_path, "artist_name.odcs.yaml")

    with pytest.raises(DataContractException) as exc:
        resolve_data_contract(str(path), inline_references=True)
    assert "is not a valid ODCS property" in str(exc.value)


@responses.activate
def test_a_url_without_a_file_suffix_is_still_fetched(tmp_path, monkeypatch):
    """The routing rule: a fragment-less url is only read from disk when it
    names a file. A path on the configured host keeps being fetched."""
    monkeypatch.setenv("ENTROPY_DATA_HOST", "https://api.entropy-data.com")
    responses.add(
        responses.GET,
        "https://api.entropy-data.com/definitions/sales/artist_name",
        body=b'{"name": "artist_name", "description": "from the host"}',
        status=200,
    )
    path = _referencing_contract(tmp_path, "/definitions/sales/artist_name")

    prop = _first_property(resolve_data_contract(str(path), inline_references=True))

    assert prop.description == "from the host"


# --- Chained references ---------------------------------------------------


def test_reference_chain_is_resolved_transitively(tmp_path):
    """technical -> business -> glossary: the business attribute may itself
    delegate, and the technical contract still ends up with the meaning."""
    _write(
        tmp_path,
        "glossary.odcs.yaml",
        """
        apiVersion: v3.1.0
        kind: DataContract
        id: glossary
        version: 1.0.0
        status: active
        schema:
          - name: terms
            id: terms
            properties:
              - name: artist
                id: artist
                description: A performing musician.
                businessName: Artist
        """,
    )
    _write(
        tmp_path,
        "business.odcs.yaml",
        """
        apiVersion: v3.1.0
        kind: DataContract
        id: business
        version: 1.0.0
        status: active
        schema:
          - name: top_artists
            id: top_artists_by_year_ba
            properties:
              - name: Artist Name
                id: artist_name
                authoritativeDefinitions:
                  - type: businessDefinition
                    url: glossary.odcs.yaml#schema/terms/properties/artist
        """,
    )
    path = _referencing_contract(tmp_path, "business.odcs.yaml#schema/top_artists_by_year_ba/properties/artist_name")

    prop = _first_property(resolve_data_contract(str(path), inline_references=True))

    assert prop.description == "A performing musician."
    assert prop.businessName == "Artist"


def test_reference_cycle_is_reported(tmp_path):
    """Two contracts referencing each other must fail with a cycle error rather
    than recursing until the stack runs out."""
    _write(
        tmp_path,
        "business.odcs.yaml",
        """
        apiVersion: v3.1.0
        kind: DataContract
        id: business
        version: 1.0.0
        status: active
        schema:
          - name: top_artists
            id: top_artists_by_year_ba
            properties:
              - name: Artist Name
                id: artist_name
                authoritativeDefinitions:
                  - type: businessDefinition
                    url: technical.odcs.yaml#schema/mv_top_artists/properties/artist_name
        """,
    )
    path = _referencing_contract(tmp_path, "business.odcs.yaml#schema/top_artists_by_year_ba/properties/artist_name")

    with pytest.raises(DataContractException) as exc:
        resolve_data_contract(str(path), inline_references=True)
    assert "cycle" in str(exc.value)


# --- Failure modes --------------------------------------------------------


def test_missing_file_rejects_the_contract(tmp_path):
    path = _referencing_contract(tmp_path, "missing.odcs.yaml#schema/x/properties/y")

    with pytest.raises(DataContractException) as exc:
        resolve_data_contract(str(path), inline_references=True)
    assert "does not exist" in str(exc.value)


def test_unknown_schema_object_names_the_available_ones(tmp_path):
    _business_contract(tmp_path)
    path = _referencing_contract(tmp_path, "business.odcs.yaml#schema/nope/properties/artist_name")

    with pytest.raises(DataContractException) as exc:
        resolve_data_contract(str(path), inline_references=True)
    msg = str(exc.value)
    assert "no schema object 'nope'" in msg
    assert "top_artists_by_year_ba" in msg


def test_unknown_property_names_the_available_ones(tmp_path):
    _business_contract(tmp_path)
    path = _referencing_contract(tmp_path, "business.odcs.yaml#schema/top_artists_by_year_ba/properties/nope")

    with pytest.raises(DataContractException) as exc:
        resolve_data_contract(str(path), inline_references=True)
    msg = str(exc.value)
    assert "no property 'nope'" in msg
    assert "artist_name" in msg


def test_malformed_fragment_is_rejected(tmp_path):
    _business_contract(tmp_path)
    path = _referencing_contract(tmp_path, "business.odcs.yaml#top_artists_by_year_ba/artist_name")

    with pytest.raises(DataContractException) as exc:
        resolve_data_contract(str(path), inline_references=True)
    assert "must start with 'schema/<schema>'" in str(exc.value)


def test_fragment_pointing_at_a_schema_object_is_rejected(tmp_path):
    """A schema object is not a property and cannot be inlined into one."""
    _business_contract(tmp_path)
    path = _referencing_contract(tmp_path, "business.odcs.yaml#schema/top_artists_by_year_ba")

    with pytest.raises(DataContractException) as exc:
        resolve_data_contract(str(path), inline_references=True)
    assert "must point at a property" in str(exc.value)


def test_contract_without_a_file_location_cannot_resolve_a_relative_reference():
    """Resolving `<file>#<fragment>` needs a directory to resolve against; a
    contract handed over as a string has none."""
    contract_str = dedent(
        """
        apiVersion: v3.1.0
        kind: DataContract
        id: technical
        version: 1.0.0
        status: active
        schema:
          - name: t
            properties:
              - name: artist_name
                authoritativeDefinitions:
                  - type: businessDefinition
                    url: business.odcs.yaml#schema/b/properties/p
        """
    ).lstrip()

    with pytest.raises(DataContractException) as exc:
        resolve_data_contract(data_contract_str=contract_str, inline_references=True)
    assert "no directory to resolve the reference against" in str(exc.value)


def test_no_inline_references_skips_local_resolution(tmp_path):
    """`--no-inline-references` leaves the contract exactly as written, even
    when the reference is broken."""
    path = _referencing_contract(tmp_path, "missing.odcs.yaml#schema/x/properties/y")

    prop = _first_property(resolve_data_contract(str(path), inline_references=False))

    assert prop.description is None


# --- Interaction with the existing HTTP-based resolution ------------------


@responses.activate
def test_the_same_type_resolves_from_a_file_or_from_a_url():
    """The link's type says what the reference means; the url's shape says
    where it lives. A `businessDefinition` pointing at a URL is fetched, the
    same type pointing at a file is read from disk (covered above)."""
    responses.add(
        responses.GET,
        "https://glossary.example.com/terms/artist",
        body=b'{"name": "artist", "description": "A performing musician."}',
        status=200,
    )
    prop = SchemaProperty(
        name="artist_name",
        authoritativeDefinitions=[
            AuthoritativeDefinition(type="businessDefinition", url="https://glossary.example.com/terms/artist")
        ],
    )
    contract = OpenDataContractStandard(
        apiVersion="v3.1.0",
        kind="DataContract",
        id="test",
        version="1.0.0",
        status="draft",
        schema=[SchemaObject(name="t", properties=[prop])],
    )

    inline_definitions_into_data_contract(contract)

    assert prop.description == "A performing musician."


@responses.activate
def test_semantics_link_wins_over_a_local_business_definition(tmp_path, monkeypatch):
    """Precedence is unchanged: a semantic concept outranks a business
    definition, and only the winning link is resolved."""
    monkeypatch.setenv("ENTROPY_DATA_HOST", "https://api.entropy-data.com")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        "https://api.entropy-data.com/sem",
        body=b'{"name": "artist", "businessName": "from-semantics"}',
        status=200,
    )
    _business_contract(tmp_path)
    path = _write(
        tmp_path,
        "technical.odcs.yaml",
        """
        apiVersion: v3.1.0
        kind: DataContract
        id: technical
        version: 1.0.0
        status: active
        schema:
          - name: mv_top_artists
            properties:
              - name: artist_name
                authoritativeDefinitions:
                  - type: businessDefinition
                    url: business.odcs.yaml#schema/top_artists_by_year_ba/properties/artist_name
                  - type: semantics
                    url: /sem
        """,
    )

    prop = _first_property(resolve_data_contract(str(path), inline_references=True))

    assert prop.businessName == "from-semantics"
    assert prop.description is None


# --- The shipped example --------------------------------------------------


def test_example_pair_resolves():
    """The documented example under examples/business-definitions/ works."""
    contract = resolve_data_contract(str(EXAMPLES / "top-artists-by-year-view.odcs.yaml"), inline_references=True)

    artist_name, year, total = contract.schema_[0].properties
    assert artist_name.description == "The artist name (not the legal name found in the passport)."
    assert artist_name.businessName == "Artist Name"
    assert artist_name.physicalType == "character"  # the technical contract keeps its own shape
    assert year.examples == [2025]
    assert total.businessName == "Total Number of Songs"
