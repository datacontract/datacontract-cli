from pydantic import BaseModel
from rdflib import RDF, BNode, Graph, Literal, Namespace, URIRef

from datacontract.export.exporter import Exporter
from datacontract.model.data_contract_specification import DataContractSpecification


class RdfExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        self.dict_args = export_args
        rdf_base = self.dict_args.get("rdf_base")
        return to_rdf_n3(data_contract_spec=data_contract, base=rdf_base)


def is_literal(property_name):
    return property_name in [
        "dataContractSpecification",
        "title",
        "version",
        "description",
        "name",
        "url",
        "type",
        "location",
        "format",
        "delimiter",
        "usage",
        "limitations",
        "billing",
        "noticePeriod",
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
    ]


def is_uriref(property_name):
    return property_name in ["model", "domain", "owner"]


def to_rdf_n3(data_contract_spec: DataContractSpecification, base) -> str:
    return to_rdf(data_contract_spec, base).serialize(format="n3")


def to_rdf(data_contract_spec: DataContractSpecification, base) -> Graph:
    if base is not None:
        g = Graph(base=base)
    else:
        g = Graph(base=Namespace(""))

    dc = Namespace("https://datacontract.com/DataContractSpecification/1.1.0/")
    dcx = Namespace("https://datacontract.com/DataContractSpecification/1.1.0/Extension/")

    g.bind("dc", dc)
    g.bind("dcx", dcx)

    this_contract = URIRef(data_contract_spec.id)

    g.add((this_contract, dc.dataContractSpecification, Literal(data_contract_spec.dataContractSpecification)))
    g.add((this_contract, dc.id, Literal(data_contract_spec.id)))
    g.add((this_contract, RDF.type, URIRef(dc + "DataContract")))

    add_info(contract=this_contract, info=data_contract_spec.info, graph=g, dc=dc, dcx=dcx)

    if data_contract_spec.terms is not None:
        add_terms(contract=this_contract, terms=data_contract_spec.terms, graph=g, dc=dc, dcx=dcx)

    for server_name, server in data_contract_spec.servers.items():
        add_server(contract=this_contract, server=server, server_name=server_name, graph=g, dc=dc, dcx=dcx)

    for model_name, model in data_contract_spec.models.items():
        add_model(contract=this_contract, model=model, model_name=model_name, graph=g, dc=dc, dcx=dcx)

    for example in data_contract_spec.examples:
        add_example(contract=this_contract, example=example, graph=g, dc=dc, dcx=dcx)

    g.commit()
    g.close()

    return g


def add_example(contract, example, graph, dc, dcx):
    an_example = BNode()
    graph.add((contract, dc["example"], an_example))
    graph.add((an_example, RDF.type, URIRef(dc + "Example")))
    for example_property in example.model_fields:
        add_triple(sub=an_example, pred=example_property, obj=example, graph=graph, dc=dc, dcx=dcx)


def add_triple(sub, pred, obj, graph, dc, dcx):
    if pred == "ref":
        pass
    elif isinstance(getattr(obj, pred), list):
        for item in getattr(obj, pred):
            add_predicate(sub=sub, pred=pred, obj=item, graph=graph, dc=dc, dcx=dcx)
    elif isinstance(getattr(obj, pred), dict):
        pass
    else:
        add_predicate(sub=sub, pred=pred, obj=obj, graph=graph, dc=dc, dcx=dcx)


def add_model(contract, model, model_name, graph, dc, dcx):
    a_model = URIRef(model_name)
    graph.add((contract, dc["model"], a_model))
    graph.add((a_model, dc.description, Literal(model.description)))
    graph.add((a_model, RDF.type, URIRef(dc + "Model")))
    for field_name, field in model.fields.items():
        a_field = BNode()
        graph.add((a_model, dc["field"], a_field))
        graph.add((a_field, RDF.type, URIRef(dc + "Field")))
        graph.add((a_field, dc["name"], Literal(field_name)))
        for field_property in field.model_fields:
            add_triple(sub=a_field, pred=field_property, obj=field, graph=graph, dc=dc, dcx=dcx)


def add_server(contract, server, server_name, graph, dc, dcx):
    a_server = URIRef(server_name)
    graph.add((contract, dc.server, a_server))
    graph.add((a_server, RDF.type, URIRef(dc + "Server")))
    for server_property_name in server.model_fields:
        add_triple(sub=a_server, pred=server_property_name, obj=server, graph=graph, dc=dc, dcx=dcx)


def add_terms(contract, terms, graph, dc, dcx):
    bnode_terms = BNode()
    graph.add((contract, dc.terms, bnode_terms))
    graph.add((bnode_terms, RDF.type, URIRef(dc + "Terms")))
    for term_name in terms.model_fields:
        add_triple(sub=bnode_terms, pred=term_name, obj=terms, graph=graph, dc=dc, dcx=dcx)


def add_info(contract, info, graph, dc, dcx):
    bnode_info = BNode()
    graph.add((contract, dc.info, bnode_info))
    graph.add((bnode_info, RDF.type, URIRef(dc + "Info")))
    graph.add((bnode_info, dc.title, Literal(info.title)))
    graph.add((bnode_info, dc.description, Literal(info.description)))
    graph.add((bnode_info, dc.version, Literal(info.version)))

    # add owner
    owner = Literal(info.owner)
    graph.add((bnode_info, dc.owner, owner))

    # add contact
    contact = BNode()
    graph.add((bnode_info, dc.contact, contact))
    graph.add((contact, RDF.type, URIRef(dc + "Contact")))
    for contact_property in info.contact.model_fields:
        add_triple(sub=contact, pred=contact_property, obj=info.contact, graph=graph, dc=dc, dcx=dcx)


def add_predicate(sub, pred, obj, graph, dc, dcx):
    if isinstance(obj, BaseModel):
        if getattr(obj, pred) is not None:
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
