import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

import yaml

from datacontract.model.run import ResultEnum, Run


def write_junit_test_results(run: Run, console, output_path: Path):
    if not output_path:
        console.print("No output path specified for JUnit test results. Skip writing JUnit test results.")
        return

    testsuite = ET.Element(
        "testsuite",
        id=str(run.runId),
        name=run.dataContractId if run.dataContractId else "Data Contract",
        tests=str(len(run.checks)),
        errors=str(count_errors(run)),
        failures=str(count_failed(run)),
        skipped=str(count_skipped(run)),
        timestamp=run.timestampStart.replace(tzinfo=None).isoformat(),
        time=str((run.timestampEnd - run.timestampStart).total_seconds()),
    )

    testsuiteProperties = ET.SubElement(testsuite, "properties")
    if run.dataContractId is not None:
        ET.SubElement(testsuiteProperties, "property", name="dataContractId", value=run.dataContractId)
    if run.dataContractVersion is not None:
        ET.SubElement(testsuiteProperties, "property", name="dataContractVersion", value=run.dataContractVersion)
    if run.dataProductId is not None:
        ET.SubElement(testsuiteProperties, "property", name="dataProductId", value=run.dataProductId)
    if run.outputPortId is not None:
        ET.SubElement(testsuiteProperties, "property", name="outputPortId", value=run.outputPortId)
    if run.server is not None:
        ET.SubElement(testsuiteProperties, "property", name="server", value=run.server)

    for check in run.checks:
        testcase = ET.SubElement(testsuite, "testcase", classname=to_class_name(check), name=to_testcase_name(check))
        if check.result == ResultEnum.passed:
            pass
        elif check.result == ResultEnum.failed:
            failure = ET.SubElement(
                testcase,
                "failure",
                message=check.reason if check.reason else "Failed",
                type=check.category if check.category else "General",
            )
            failure.text = to_failure_text(check)
        elif check.result == ResultEnum.error:
            error = ET.SubElement(
                testcase,
                "error",
                message=check.reason if check.reason else "Error",
                type=check.category if check.category else "General",
            )
            error.text = to_failure_text(check)
        elif check.result is ResultEnum.warning:
            skipped = ET.SubElement(
                testcase,
                "skipped",
                message=check.reason if check.reason else "Warning",
                type=check.category if check.category else "General",
            )
            skipped.skipped = to_failure_text(check)
        else:
            ET.SubElement(
                testcase,
                "skipped",
                message=check.reason if check.reason else "None",
                type=check.category if check.category else "General",
            )

    if run.logs:
        system_out = ET.SubElement(testsuite, "system-out")
        system_out.text = logs_to_system_out(run)

    xml_str: str = ET.tostring(testsuite, xml_declaration=True, encoding="utf-8")
    xml_str_pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str_pretty)
    console.print(f"JUnit test results written to {output_path}")


def to_testcase_name(check):
    if check.key:
        return check.key
    if check.name:
        return check.name
    else:
        return "unknown"


def logs_to_system_out(run):
    result = ""
    for log in run.logs:
        result += f"{log.timestamp} {log.level}: {log.message}\n"
    return result


def to_class_name(check):
    if check.model and check.field:
        return f"{check.model}.{check.field}"
    elif check.model:
        return check.model
    elif check.field:
        return check.field
    else:
        return "general"


def to_failure_text(check):
    return (
        f"Name: {check.name}\n"
        f"Engine: {check.engine}\n"
        f"Implementation:\n{check.implementation}\n\n"
        f"Result: {check.result.value if check.result is not None else ''}\n"
        f"Reason: {check.reason}\n"
        f"Details: {check.details}\n"
        f"Diagnostics:\n{yaml.dump(check.diagnostics, default_flow_style=False)}"
    )


def count_errors(run):
    return sum(1 for check in run.checks if check.result == ResultEnum.error)


def count_failed(run):
    return sum(1 for check in run.checks if check.result == ResultEnum.failed)


def count_skipped(run):
    return sum(1 for check in run.checks if check.result is None)
