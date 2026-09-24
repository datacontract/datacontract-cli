from datacontract.lint.files import read_file


def test_read_file_decodes_as_utf8_on_a_non_utf8_default_encoding(tmp_path, non_utf8_default_encoding):
    contract_file = tmp_path / "accented.yaml"
    contract_file.write_text('name: "Libellé, Catégorie, Donnée"\n', encoding="utf-8")

    content = read_file(str(contract_file))

    assert content == 'name: "Libellé, Catégorie, Donnée"\n'
