from open_data_contract_standard.model import OpenDataContractStandard
from pydantic import BaseModel
from rdflib import RDF, BNode, Graph, Literal, Namespace, URIRef

from datacontract.export.exporter import Exporter


class RdfExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        self.dict_args = export_args
        rdf_base = self.dict_args.get("rdf_base")
        return to_rdf_n3(data_contract=data_contract, base=rdf_base)


def is_literal(property_name):
    return property_name in [
        "apiVersion",
        "kind",
        "id",
        "name",
        "version",
        "description",
        "status",
        "domain",
        "dataProduct",
        "tenant",
        "type",
        "location",
        "format",
        "delimiter",
        "required",
        "unique",
        "minLength",
        "maxLength",
        "example",
        "pii",
        "classification",
        "data",
        "enum",
        "minimum",
        "maximum",
        "patterns",
        "logicalType",
        "physicalType",
    ]


def is_uriref(property_name):
    return property_name in ["model", "domain", "owner", "team"]


def to_rdf_n3(data_contract: OpenDataContractStandard, base) -> str:
    return to_rdf(data_contract, base).serialize(format="n3")


def to_rdf(data_contract: OpenDataContractStandard, base) -> Graph:
    if base is not None:
        g = Graph(base=base)
    else:
        g = Graph(base=Namespace(""))

    # Use ODCS namespace
    odcs = Namespace("https://github.com/bitol-io/open-data-contract-standard/")
    odcsx = Namespace("https://github.com/bitol-io/open-data-contract-standard/extension/")

    g.bind("odcs", odcs)
    g.bind("odcsx", odcsx)

    this_contract = URIRef(data_contract.id)

    g.add((this_contract, odcs.apiVersion, Literal(data_contract.apiVersion)))
    g.add((this_contract, odcs.kind, Literal(data_contract.kind)))
    g.add((this_contract, odcs.id, Literal(data_contract.id)))
    g.add((this_contract, RDF.type, URIRef(odcs + "DataContract")))

    add_basic_info(contract=this_contract, data_contract=data_contract, graph=g, odcs=odcs, odcsx=odcsx)

    # Add servers
    if data_contract.servers:
        for server in data_contract.servers:
            add_server(contract=this_contract, server=server, graph=g, odcs=odcs, odcsx=odcsx)

    # Add schema
    if data_contract.schema_:
        for schema_obj in data_contract.schema_:
            add_schema(contract=this_contract, schema_obj=schema_obj, graph=g, odcs=odcs, odcsx=odcsx)

    g.commit()
    g.close()

    return g


def add_basic_info(contract, data_contract: OpenDataContractStandard, graph, odcs, odcsx):
    bnode_info = BNode()
    graph.add((contract, odcs.info, bnode_info))
    graph.add((bnode_info, RDF.type, URIRef(odcs + "Info")))

    if data_contract.name:
        graph.add((bnode_info, odcs.name, Literal(data_contract.name)))
    if data_contract.description:
        desc = data_contract.description
        if hasattr(desc, 'purpose') and desc.purpose:
            graph.add((bnode_info, odcs.description, Literal(desc.purpose)))
        elif isinstance(desc, str):
            graph.add((bnode_info, odcs.description, Literal(desc)))
    if data_contract.version:
        graph.add((bnode_info, odcs.version, Literal(data_contract.version)))

    # Add team/owner
    if data_contract.team:
        graph.add((bnode_info, odcs.team, Literal(data_contract.team.name)))


def add_server(contract, server, graph, odcs, odcsx):
    a_server = URIRef(server.server or "default")
    graph.add((contract, odcs.server, a_server))
    graph.add((a_server, RDF.type, URIRef(odcs + "Server")))
    for server_property_name in server.model_fields:
        add_triple(sub=a_server, pred=server_property_name, obj=server, graph=graph, dc=odcs, dcx=odcsx)


def add_schema(contract, schema_obj, graph, odcs, odcsx):
    a_model = URIRef(schema_obj.name)
    graph.add((contract, odcs.schema_, a_model))
    graph.add((a_model, odcs.description, Literal(schema_obj.description or "")))
    graph.add((a_model, RDF.type, URIRef(odcs + "Schema")))

    if schema_obj.properties:
        for prop in schema_obj.properties:
            a_property = BNode()
            graph.add((a_model, odcs["property"], a_property))
            graph.add((a_property, RDF.type, URIRef(odcs + "Property")))
            graph.add((a_property, odcs["name"], Literal(prop.name)))
            for field_property in prop.model_fields:
                add_triple(sub=a_property, pred=field_property, obj=prop, graph=graph, dc=odcs, dcx=odcsx)


def add_triple(sub, pred, obj, graph, dc, dcx):
    if pred == "ref":
        pass
    elif isinstance(getattr(obj, pred, None), list):
        for item in getattr(obj, pred):
            add_predicate(sub=sub, pred=pred, obj=item, graph=graph, dc=dc, dcx=dcx)
    elif isinstance(getattr(obj, pred, None), dict):
        pass
    else:
        add_predicate(sub=sub, pred=pred, obj=obj, graph=graph, dc=dc, dcx=dcx)


def add_predicate(sub, pred, obj, graph, dc, dcx):
    if isinstance(obj, BaseModel):
        if getattr(obj, pred, None) is not None:
            if is_literal(pred):
                graph.add((sub, dc[pred], Literal(getattr(obj, pred))))
            elif is_uriref(pred):
                graph.add((sub, dc[pred], URIRef(getattr(obj, pred))))
            else:
                # treat it as an extension
                graph.add((sub, dcx[pred], Literal(getattr(obj, pred))))
    else:
        # assume primitive
        if is_literal(pred):
            graph.add((sub, dc[pred], Literal(obj)))
        elif is_uriref(pred):
            graph.add((sub, dc[pred], URIRef(obj)))
        else:
            # treat it as an extension
            graph.add((sub, dcx[pred], Literal(obj)))
