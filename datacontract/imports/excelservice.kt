package datameshmanager.datacontract

import com.fasterxml.jackson.databind.ObjectMapper
import org.apache.poi.ss.usermodel.Cell
import org.apache.poi.ss.usermodel.CellType
import org.apache.poi.ss.usermodel.Row
import org.apache.poi.ss.usermodel.Sheet
import org.apache.poi.ss.usermodel.Workbook
import org.apache.poi.ss.usermodel.WorkbookFactory
import org.apache.poi.ss.util.CellRangeAddress
import org.apache.poi.ss.util.CellReference
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import org.springframework.web.client.RestTemplate
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream

/**
 * Service to handle Excel import/export for OpenDataContract specifications
 */
@Service
class DataContractExcelService {

  companion object {
    const val ODCS_EXCEL_TEMPLATE_URL =
      "https://github.com/datacontract/open-data-contract-standard-excel-template/raw/refs/heads/main/odcs-template.xlsx"
  }

  private val logger = LoggerFactory.getLogger(this::class.java)
  private val restTemplate = RestTemplate()
  private val objectMapper = ObjectMapper()

  /**
   * Export an ODCS object to Excel format
   * @param odcs The OpenDataContractStandard object to export
   * @return Byte array containing the Excel file with ODCS data
   */
  fun exportToExcel(odcs: OpenDataContractStandard): ByteArray {

    val workbook = createWorkbookFromTemplateUrl(ODCS_EXCEL_TEMPLATE_URL)

    try {
      fillFundamentals(workbook, odcs)
      fillSchema(workbook, odcs)
      fillCustomProperties(workbook, odcs)
      fillSupport(workbook, odcs)
      fillTeam(workbook, odcs)
      fillRoles(workbook, odcs)
      fillSlaProperties(workbook, odcs)
      fillServers(workbook, odcs)
      fillPricing(workbook, odcs)

      // Set focus on the Fundamentals sheet
      workbook.setActiveSheet(workbook.getSheetIndex(workbook.getSheet("Fundamentals")))

      // necessary to compute formulas (e.g., owner lookup)
      workbook.setForceFormulaRecalculation(true);

      // Write to output stream
      val outputStream = ByteArrayOutputStream()
      workbook.write(outputStream)
      return outputStream.toByteArray()
    } finally {
      workbook.close()
    }
  }


  private fun fillFundamentals(
    workbook: Workbook,
    odcs: OpenDataContractStandard
  ) {
    setCellValueByName(workbook, "apiVersion", odcs.apiVersion)
    setCellValueByName(workbook, "kind", odcs.kind)
    setCellValueByName(workbook, "id", odcs.id)
    setCellValueByName(workbook, "name", odcs.name)
    setCellValueByName(workbook, "version", odcs.version)
    setCellValueByName(workbook, "status", odcs.status)
    setCellValueByName(workbook, "domain", odcs.domain)
    setCellValueByName(workbook, "dataProduct", odcs.dataProduct)
    setCellValueByName(workbook, "tenant", odcs.tenant)

    setCellValueByName(workbook, "owner", odcs.customProperties?.find { it.property == "owner" }?.value?.toString())

    setCellValueByName(workbook, "slaDefaultElement", odcs.slaDefaultElement)

    // Set description fields
    odcs.description?.let {
      setCellValueByName(workbook, "description.purpose", it.purpose)
      setCellValueByName(workbook, "description.limitations", it.limitations)
      setCellValueByName(workbook, "description.usage", it.usage)
    }

    // Set tags as a comma-separated string
    setCellValueByName(workbook, "tags", odcs.tags?.joinToString(","))
  }

  private fun fillPricing(
    workbook: Workbook,
    odcs: OpenDataContractStandard
  ) {
    setCellValueByName(workbook, "price.priceAmount", odcs.price?.priceAmount)
    setCellValueByName(workbook, "price.priceCurrency", odcs.price?.priceCurrency)
    setCellValueByName(workbook, "price.priceUnit", odcs.price?.priceUnit)
  }

  private fun fillSchema(
    workbook: Workbook,
    odcs: OpenDataContractStandard
  ) {
    // get template sheet "Schema <table_name>" and copy it for each schema
    val schemaTemplateSheet = workbook.getSheet("Schema <table_name>")

    // iterate over schemas, copy the template sheet and fill in the schema data
    odcs.schema?.forEach { schema ->
      val newSheet = workbook.cloneSheet(workbook.getSheetIndex(schemaTemplateSheet))
      workbook.setSheetName(workbook.getSheetIndex(newSheet), "Schema ${schema.name}")
      workbook.setSheetOrder(newSheet.sheetName, workbook.getSheetIndex(schemaTemplateSheet))
      copySheetNames(schemaTemplateSheet, newSheet)

      // Fill in schema information
      fillSchema(newSheet, schema)
    }

    // Remove the template sheet
    workbook.removeSheetAt(workbook.getSheetIndex(schemaTemplateSheet))
  }

  private fun fillCustomProperties(
    workbook: Workbook,
    odcs: OpenDataContractStandard
  ) {
    val customPropertiesSheet = workbook.getSheet("Custom Properties")
    val ref = nameToRef(workbook, "customProperties") ?: throw RuntimeException("No schema.properties found")
    val cellRangeAddress = CellRangeAddress.valueOf(ref)
    // ignore the first row
    val customPropertiesHeaderRowIndex = cellRangeAddress.firstRow
    // for every custom property, add info in a new row
    odcs.customProperties?.filter { it.property != "owner" }?.filter { !it.property.isNullOrBlank() }
      ?.forEachIndexed { index, customProperty ->
        val row = customPropertiesSheet.getRow(customPropertiesHeaderRowIndex + 1 + index)
        setCellValue(row, 0, customProperty.property)
        when (customProperty.value) {
          is String -> setCellValue(row, 1, customProperty.value)
          is Int -> setCellValue(row, 1, customProperty.value.toDouble())
          is Double -> setCellValue(row, 1, customProperty.value)
          is Boolean -> setCellValue(row, 1, customProperty.value)
          is Object -> setCellValue(row, 1, objectMapper.writeValueAsString(customProperty.value))

          else -> setCellValue(row, 1, customProperty.value.toString())
        }
      }
  }

  private fun fillSupport(workbook: Workbook, odcs: OpenDataContractStandard) {
    val ref = nameToRef(workbook, "support") ?: throw RuntimeException("No support found")
    val cellRangeAddress = CellRangeAddress.valueOf(ref)
    val sheet = workbook.getSheet("Support") // workaround

    // find row index with a cell value Property
    val propertiesHeaderRowIndex = cellRangeAddress.firstRow
    val skipHeaderRow = 1
    val headers = getHeadersFromHeaderRow(sheet, propertiesHeaderRowIndex)

    odcs.support?.forEachIndexed { supportChannelIndex, supportChannel ->
      val row = sheet.getRow(propertiesHeaderRowIndex + skipHeaderRow + supportChannelIndex)

      headers.forEach { (cellIndex, headerName) ->
        when (headerName.lowercase()) {
          "channel" -> setCellValue(row, cellIndex, supportChannel.channel)
          "channel url" -> setCellValue(row, cellIndex, supportChannel.url)
          "description" -> setCellValue(row, cellIndex, supportChannel.description)
          "tool" -> setCellValue(row, cellIndex, supportChannel.tool)
          "scope" -> setCellValue(row, cellIndex, supportChannel.scope)
          "invitation url" -> setCellValue(row, cellIndex, supportChannel.invitationUrl)
        }
      }
    }
  }

  private fun fillTeam(workbook: Workbook, odcs: OpenDataContractStandard) {
    val ref = nameToRef(workbook, "team") ?: throw RuntimeException("No support found")
    val cellRangeAddress = CellRangeAddress.valueOf(ref)
    val sheet = workbook.getSheet("Team") // workaround

    // find row index with a cell value Property
    val propertiesHeaderRowIndex = cellRangeAddress.firstRow
    val skipHeaderRow = 1
    val headers = getHeadersFromHeaderRow(sheet, propertiesHeaderRowIndex)

    odcs.team?.forEachIndexed { teamIndex, teamMember ->
      val row = sheet.getRow(propertiesHeaderRowIndex + skipHeaderRow + teamIndex)

      headers.forEach { (cellIndex, headerName) ->
        when (headerName.lowercase()) {
          "username" -> setCellValue(row, cellIndex, teamMember.username)
          "name" -> setCellValue(row, cellIndex, teamMember.name)
          "description" -> setCellValue(row, cellIndex, teamMember.description)
          "role" -> setCellValue(row, cellIndex, teamMember.role)
          "date in" -> setCellValue(row, cellIndex, teamMember.dateIn)
          "date out" -> setCellValue(row, cellIndex, teamMember.dateOut)
          "replaced by username" -> setCellValue(row, cellIndex, teamMember.replacedByUsername)
        }
      }
    }
  }

  private fun fillRoles(workbook: Workbook, odcs: OpenDataContractStandard) {
    val ref = nameToRef(workbook, "roles") ?: throw RuntimeException("No support found")
    val cellRangeAddress = CellRangeAddress.valueOf(ref)
    val sheet = workbook.getSheet("Roles")

    // find row index with a cell value Property
    val propertiesHeaderRowIndex = cellRangeAddress.firstRow
    val skipHeaderRow = 1
    val headers = getHeadersFromHeaderRow(sheet, propertiesHeaderRowIndex)

    odcs.roles?.forEachIndexed { roleIndex, role ->
      val row = sheet.getRow(propertiesHeaderRowIndex + skipHeaderRow + roleIndex)

      headers.forEach { (cellIndex, headerName) ->
        when (headerName.lowercase()) {
          "role" -> setCellValue(row, cellIndex, role.role)
          "description" -> setCellValue(row, cellIndex, role.description)
          "access" -> setCellValue(row, cellIndex, role.access)
          "1st level approvers" -> setCellValue(row, cellIndex, role.firstLevelApprovers)
          "2nd level approvers" -> setCellValue(row, cellIndex, role.secondLevelApprovers)
        }
      }
    }
  }

  private fun fillSlaProperties(workbook: Workbook, odcs: OpenDataContractStandard) {
    val ref = nameToRef(workbook, "slaProperties") ?: throw RuntimeException("No support found")
    val cellRangeAddress = CellRangeAddress.valueOf(ref)
    val sheet = workbook.getSheet("SLA")

    // find row index with a cell value Property
    val propertiesHeaderRowIndex = cellRangeAddress.firstRow
    val skipHeaderRow = 1
    val headers = getHeadersFromHeaderRow(sheet, propertiesHeaderRowIndex)

    odcs.slaProperties?.forEachIndexed { roleIndex, role ->
      val row = sheet.getRow(propertiesHeaderRowIndex + skipHeaderRow + roleIndex)

      headers.forEach { (cellIndex, headerName) ->
        when (headerName.lowercase()) {
          "property" -> setCellValue(row, cellIndex, role.property)
          "value" -> setCellValue(row, cellIndex, role.value)
          "extended value" -> setCellValue(row, cellIndex, role.valueExt)
          "unit" -> setCellValue(row, cellIndex, role.unit)
          "element" -> setCellValue(row, cellIndex, role.element)
          "driver" -> setCellValue(row, cellIndex, role.driver)
        }
      }
    }
  }


  private fun copySheetNames(schemaTemplateSheet: Sheet, newSheet: Sheet) {
    val names = schemaTemplateSheet.workbook.allNames.filter { it.sheetName == schemaTemplateSheet.sheetName }
    names.forEach { name ->
      val newName = newSheet.workbook.createName()
      newName.setSheetIndex(newSheet.workbook.getSheetIndex(newSheet))
      newName.setNameName(name.nameName)
      newName.refersToFormula = name.refersToFormula.replace(schemaTemplateSheet.sheetName, newSheet.sheetName)
    }
  }

  private fun createWorkbookFromTemplateUrl(templateUrl: String): Workbook {
    val templateBytes = restTemplate.getForObject(templateUrl, ByteArray::class.java)
      ?: throw RuntimeException("Failed to download template from URL: $templateUrl")
    val workbook = WorkbookFactory.create(ByteArrayInputStream(templateBytes))
    return workbook
  }

  /**
   * Import an ODCS object from Excel format
   * @param excelBytes The Excel file as byte array
   * @return The imported OpenDataContractStandard object
   */
  fun importFromExcel(excelBytes: ByteArray): OpenDataContractStandard {
    val workbook = WorkbookFactory.create(ByteArrayInputStream(excelBytes))

    try {
      val owner = getCellValueByName(workbook, "owner")

      // Build description object
      val description = OpenDataContractStandard.Description(
        purpose = getCellValueByName(workbook, "description.purpose"),
        limitations = getCellValueByName(workbook, "description.limitations"),
        usage = getCellValueByName(workbook, "description.usage"),
        authoritativeDefinitions = null,
        customProperties = null,
      )

      val tags = getCellValueByName(workbook, "tags")?.split(",")?.filter { it.isNotBlank() }

      val schemas = importSchema(workbook)
      val support = importSupport(workbook)
      val team = importTeam(workbook)
      val roles = importRoles(workbook)
      val slaProperties = importSlaProperties(workbook)
      val servers = importServers(workbook)
      val price = importPrice(workbook)
      val customProperties = importCustomProperties(owner, workbook)

      return OpenDataContractStandard(
        apiVersion = getCellValueByName(workbook, "apiVersion"),
        kind = getCellValueByName(workbook, "kind"),
        id = getCellValueByName(workbook, "id"),
        name = getCellValueByName(workbook, "name"),
        version = getCellValueByName(workbook, "version"),
        status = getCellValueByName(workbook, "status"),
        domain = getCellValueByName(workbook, "domain"),
        dataProduct = getCellValueByName(workbook, "dataProduct"),
        tenant = getCellValueByName(workbook, "tenant"),
        description = description,
        tags = tags,
        schema = schemas,
        support = support,
        price = price,
        team = team,
        roles = roles,
        slaDefaultElement = getCellValueByName(workbook, "slaDefaultElement"),
        slaProperties = slaProperties,
        servers = servers,
        customProperties = customProperties,
        authoritativeDefinitions = null,
      )
    } finally {
      workbook.close()
    }
  }

  private fun importSchema(workbook: Workbook?): List<OpenDataContractStandard.Schema>? {
    if (workbook == null) {
      return null
    }

    return workbook.sheetIterator().asSequence()
      .filter { it.sheetName.startsWith("Schema ", ignoreCase = true) }
      .map { sheet ->
        val schemaName = getCellValueByName(sheet, "schema.name") ?: return@map null

        OpenDataContractStandard.Schema(
          name = schemaName,
          logicalType = "object",
          physicalType = getCellValueByName(sheet, "schema.physicalType"),
          physicalName = getCellValueByName(sheet, "schema.physicalName"),
          description = getCellValueByName(sheet, "schema.description"),
          authoritativeDefinitions = null,
          tags = getCellValueByName(sheet, "schema.tags")?.split(",")?.filter { it.isNotBlank() },
          properties = importProperties(sheet),
          quality = null,
          customProperties = null,
          businessName = getCellValueByName(sheet, "schema.businessName"),
          dataGranularityDescription = getCellValueByName(sheet, "schema.dataGranularityDescription"),
        )
      }
      .filterNotNull()
      .toList()
  }

  private fun importPrice(workbook: Workbook): OpenDataContractStandard.Price? {
    val result = OpenDataContractStandard.Price(
      priceAmount = getCellValueByName(workbook, "price.priceAmount"),
      priceCurrency = getCellValueByName(workbook, "price.priceCurrency"),
      priceUnit = getCellValueByName(workbook, "price.priceUnit"),
    )

    val isEmpty = result.priceAmount == null && result.priceCurrency == null && result.priceUnit == null
    if (isEmpty) {
      return null
    }

    return result
  }

  private fun importCustomProperties(
    owner: String?,
    workbook: Workbook
  ): MutableList<OpenDataContractStandard.CustomProperty> {
    val customProperties: MutableList<OpenDataContractStandard.CustomProperty> = mutableListOf()
    customProperties.add(
      OpenDataContractStandard.CustomProperty(
        property = "owner",
        value = owner,
      ),
    )
    nameToRef(workbook, "customProperties")?.let { ref ->
      val cellRangeAddress = CellRangeAddress.valueOf(ref)
      val customPropertiesHeaderRowIndex = cellRangeAddress.firstRow
      val customPropertiesSheet = workbook.getSheetAt(workbook.getSheetIndex("Custom Properties"))
      for (rowIndex in customPropertiesHeaderRowIndex..cellRangeAddress.lastRow) {
        val row = customPropertiesSheet.getRow(rowIndex) ?: continue
        val propertyName = getCellValueAsString(row.getCell(0))
        if (propertyName == "owner") {
          continue
        }

        val valueCell = row.getCell(1)
        val propertyValue = parsePropertyValue(valueCell)
        if (!propertyName.isNullOrBlank()) {
          customProperties.add(
            OpenDataContractStandard.CustomProperty(
              property = propertyName,
              value = propertyValue,
            ),
          )
        }
      }
    }
    return customProperties
  }

  private fun importSupport(workbook: Workbook): MutableList<OpenDataContractStandard.SupportChannel>? =
    nameToRef(workbook, "support")?.let { ref ->
      val cellRangeAddress = CellRangeAddress.valueOf(ref)
      val supportSheet = workbook.getSheet("Support")
      val supportHeaderRowIndex = cellRangeAddress.firstRow
      val headerFields = getHeadersFromHeaderRow(supportSheet, supportHeaderRowIndex)

      val channels = mutableListOf<OpenDataContractStandard.SupportChannel>()

      for (rowIndex in supportHeaderRowIndex + 1..cellRangeAddress.lastRow) {
        val row = supportSheet.getRow(rowIndex) ?: continue

        var channel: String? = null
        var url: String? = null
        var description: String? = null
        var tool: String? = null
        var scope: String? = null
        var invitationUrl: String? = null

        headerFields.forEach { (cellIndex, headerName) ->
          when (headerName.lowercase()) {
            "channel" -> channel = getCellValueAsString(row.getCell(cellIndex))
            "channel url" -> url = getCellValueAsString(row.getCell(cellIndex))
            "description" -> description = getCellValueAsString(row.getCell(cellIndex))
            "tool" -> tool = getCellValueAsString(row.getCell(cellIndex))
            "scope" -> scope = getCellValueAsString(row.getCell(cellIndex))
            "invitation url" -> invitationUrl = getCellValueAsString(row.getCell(cellIndex))
          }
        }

        if (!channel.isNullOrBlank()) {
          channels.add(
            OpenDataContractStandard.SupportChannel(
              channel = channel,
              url = url,
              description = description,
              tool = tool,
              scope = scope,
              invitationUrl = invitationUrl,
            ),
          )
        }
      }
      channels
    }

  private fun importTeam(workbook: Workbook): MutableList<OpenDataContractStandard.TeamMember>? {
    return nameToRef(workbook, "team")?.let { ref ->
      val cellRangeAddress = CellRangeAddress.valueOf(ref)
      val teamSheet = workbook.getSheet("Team")
      val teamHeaderRowIndex = cellRangeAddress.firstRow
      val headerFields = getHeadersFromHeaderRow(teamSheet, teamHeaderRowIndex)

      val teamMembers = mutableListOf<OpenDataContractStandard.TeamMember>()

      for (rowIndex in teamHeaderRowIndex + 1..cellRangeAddress.lastRow) {
        val row = teamSheet.getRow(rowIndex) ?: continue

        var username: String? = null
        var name: String? = null
        var description: String? = null
        var role: String? = null
        var dateIn: String? = null
        var dateOut: String? = null
        var replacedByUsername: String? = null

        headerFields.forEach { (cellIndex, headerName) ->
          when (headerName.lowercase()) {
            "username" -> username = getCellValueAsString(row.getCell(cellIndex))
            "name" -> name = getCellValueAsString(row.getCell(cellIndex))
            "description" -> description = getCellValueAsString(row.getCell(cellIndex))
            "role" -> role = getCellValueAsString(row.getCell(cellIndex))
            "date in" -> dateIn = getCellValueAsString(row.getCell(cellIndex))
            "date out" -> dateOut = getCellValueAsString(row.getCell(cellIndex))
            "replaced by username" -> replacedByUsername = getCellValueAsString(row.getCell(cellIndex))
          }
        }

        if (!name.isNullOrBlank() || !username.isNullOrBlank() || !role.isNullOrBlank()) {
          teamMembers.add(
            OpenDataContractStandard.TeamMember(
              username = username,
              name = name,
              description = description,
              role = role,
              dateIn = dateIn,
              dateOut = dateOut,
              replacedByUsername = replacedByUsername,
            ),
          )
        }
      }
      teamMembers
    }
  }

  private fun importRoles(workbook: Workbook): MutableList<OpenDataContractStandard.Role>? {
    val rolesSheet = workbook.getSheet("Roles")

    val ref = nameToRef(rolesSheet, "roles")
    if (ref == null) {
      return null
    }

    val cellRangeAddress = CellRangeAddress.valueOf(ref)
    val rolesRowIndex = cellRangeAddress.firstRow
    val headerFields = getHeadersFromHeaderRow(rolesSheet, rolesRowIndex)

    val roles = mutableListOf<OpenDataContractStandard.Role>()

    for (rowIndex in rolesRowIndex + 1..cellRangeAddress.lastRow) {
      val row = rolesSheet.getRow(rowIndex) ?: continue

      var role: String? = null
      var description: String? = null
      var access: String? = null
      var firstLevelApprovers: String? = null
      var secondLevelApprovers: String? = null

      headerFields.forEach { (cellIndex, headerName) ->
        when (headerName.lowercase()) {
          "role" -> role = getCellValueAsString(row.getCell(cellIndex))
          "description" -> description = getCellValueAsString(row.getCell(cellIndex))
          "access" -> access = getCellValueAsString(row.getCell(cellIndex))
          "1st level approvers" -> firstLevelApprovers = getCellValueAsString(row.getCell(cellIndex))
          "2nd level approvers" -> secondLevelApprovers = getCellValueAsString(row.getCell(cellIndex))
        }
      }

      if (!role.isNullOrBlank()) {
        roles.add(
          OpenDataContractStandard.Role(
            role = role,
            description = description,
            access = access,
            firstLevelApprovers = firstLevelApprovers,
            secondLevelApprovers = secondLevelApprovers,
            customProperties = null,
          ),
        )
      }
    }
    return roles


  }

  private fun importServers(workbook: Workbook): MutableList<OpenDataContractStandard.Server>? {

    val sheet = workbook.getSheet("Servers") ?: return null
    val firstServerCell = findCellByName(sheet, "servers.server") ?: return null

    val serverRowIndex = firstServerCell.rowIndex
    val serverRow = sheet.getRow(serverRowIndex) ?: return null
    val columnIndex = firstServerCell.columnIndex
    var index = 0
    val servers = mutableListOf<OpenDataContractStandard.Server>()
    while (getCellValueAsString(serverRow.getCell(columnIndex + index))?.isNotBlank() ?: false) {
      val server = importServer(workbook, index)
      if (server != null) {
        servers.add(server)
      }


      index++
    }

    return servers
  }

  private fun importServer(workbook: Workbook, columnIndex: Int): OpenDataContractStandard.Server? {
    val sheet = workbook.getSheet("Servers") ?: return null
    val server = getCellValueAsString(sheet, columnIndex, "servers.server")
    val description = getCellValueAsString(sheet, columnIndex, "servers.description")
    val environment = getCellValueAsString(sheet, columnIndex, "servers.environment")
    val type = getCellValueAsString(sheet, columnIndex, "servers.type")
    val result = OpenDataContractStandard.Server(
      server = server,
      description = description,
      environment = environment,
      type = type,
      project = null,
      dataset = null,
      location = null,
      delimiter = null,
      endpointUrl = null,
      account = null,
      database = null,
      schema = null,
      warehouse = null,
      table = null,
      view = null,
      catalog = null,
      port = null,
      host = null,
      topic = null,
      path = null,
      format = null,
      stagingDir = null,
      roles = null,
      customProperties = null,
    )
    when (result.type) {
      "azure" -> {
        result.location = getCellValueAsString(sheet, columnIndex, "servers.azure.location")
        result.format = getCellValueAsString(sheet, columnIndex, "servers.azure.format")
        result.delimiter = getCellValueAsString(sheet, columnIndex, "servers.azure.delimiter")
      }

      "bigquery" -> {
        result.project = getCellValueAsString(sheet, columnIndex, "servers.bigquery.project")
        result.dataset = getCellValueAsString(sheet, columnIndex, "servers.bigquery.dataset")
      }

      "databricks" -> {
        result.catalog = getCellValueAsString(sheet, columnIndex, "servers.databricks.catalog")
        result.host = getCellValueAsString(sheet, columnIndex, "servers.databricks.host")
        result.schema = getCellValueAsString(sheet, columnIndex, "servers.databricks.schema")
      }

      "glue" -> {
        result.account = getCellValueAsString(sheet, columnIndex, "servers.glue.account")
        result.database = getCellValueAsString(sheet, columnIndex, "servers.glue.database")
        result.format = getCellValueAsString(sheet, columnIndex, "servers.glue.format")
        result.location = getCellValueAsString(sheet, columnIndex, "servers.glue.location")
      }

      "kafka" -> {
        result.format = getCellValueAsString(sheet, columnIndex, "servers.kafka.format")
        result.host = getCellValueAsString(sheet, columnIndex, "servers.kafka.host")
      }

      "postgres" -> {
        result.database = getCellValueAsString(sheet, columnIndex, "servers.postgres.database")
        result.host = getCellValueAsString(sheet, columnIndex, "servers.postgres.host")
        result.port = getCellValueAsString(sheet, columnIndex, "servers.postgres.port")
        result.schema = getCellValueAsString(sheet, columnIndex, "servers.postgres.schema")
      }

      "s3" -> {
        result.delimiter = getCellValueAsString(sheet, columnIndex, "servers.s3.delimiter")
        result.endpointUrl = getCellValueAsString(sheet, columnIndex, "servers.s3.endpointUrl")
        result.format = getCellValueAsString(sheet, columnIndex, "servers.s3.format")
        result.location = getCellValueAsString(sheet, columnIndex, "servers.s3.location")
      }

      "snowflake" -> {
        result.account = getCellValueAsString(sheet, columnIndex, "servers.snowflake.account")
        result.database = getCellValueAsString(sheet, columnIndex, "servers.snowflake.database")
        result.host = getCellValueAsString(sheet, columnIndex, "servers.snowflake.host")
        result.port = getCellValueAsString(sheet, columnIndex, "servers.snowflake.port")
        result.schema = getCellValueAsString(sheet, columnIndex, "servers.snowflake.schema")
        result.warehouse = getCellValueAsString(sheet, columnIndex, "servers.snowflake.warehouse")
      }

      "sqlserver" -> {
        result.database = getCellValueAsString(sheet, columnIndex, "servers.sqlserver.database")
        result.host = getCellValueAsString(sheet, columnIndex, "servers.sqlserver.host")
        result.port = getCellValueAsString(sheet, columnIndex, "servers.sqlserver.port")
        result.schema = getCellValueAsString(sheet, columnIndex, "servers.sqlserver.schema")
      }

      else -> {
        result.account = getCellValueAsString(sheet, columnIndex, "servers.custom.account")
        result.catalog = getCellValueAsString(sheet, columnIndex, "servers.custom.catalog")
        result.database = getCellValueAsString(sheet, columnIndex, "servers.custom.database")
        result.dataset = getCellValueAsString(sheet, columnIndex, "servers.custom.dataset")
        result.delimiter = getCellValueAsString(sheet, columnIndex, "servers.custom.delimiter")
        result.endpointUrl = getCellValueAsString(sheet, columnIndex, "servers.custom.endpointUrl")
        result.format = getCellValueAsString(sheet, columnIndex, "servers.custom.format")
        result.host = getCellValueAsString(sheet, columnIndex, "servers.custom.host")
        result.location = getCellValueAsString(sheet, columnIndex, "servers.custom.location")
        result.path = getCellValueAsString(sheet, columnIndex, "servers.custom.path")
        result.port = getCellValueAsString(sheet, columnIndex, "servers.custom.port")
        result.project = getCellValueAsString(sheet, columnIndex, "servers.custom.project")
        result.region = getCellValueAsString(sheet, columnIndex, "servers.custom.region")
        result.regionName = getCellValueAsString(sheet, columnIndex, "servers.custom.regionName")
        result.schema = getCellValueAsString(sheet, columnIndex, "servers.custom.schema")
        result.serviceName = getCellValueAsString(sheet, columnIndex, "servers.custom.serviceName")
        result.stagingDir = getCellValueAsString(sheet, columnIndex, "servers.custom.stagingDir")
        result.table = getCellValueAsString(sheet, columnIndex, "servers.custom.table")
        result.view = getCellValueAsString(sheet, columnIndex, "servers.custom.view")
        result.warehouse = getCellValueAsString(sheet, columnIndex, "servers.custom.warehouse")
      }
    }

    return result
  }

  private fun importSlaProperties(workbook: Workbook): MutableList<OpenDataContractStandard.SlaProperty>? {
    val slaSheet = workbook.getSheet("SLA")
    val ref = nameToRef(slaSheet, "slaProperties")
    if (ref == null) {
      return null
    }

    val cellRangeAddress = CellRangeAddress.valueOf(ref)
    val rolesRowIndex = cellRangeAddress.firstRow
    val headerFields = getHeadersFromHeaderRow(slaSheet, rolesRowIndex)

    val slaProperties = mutableListOf<OpenDataContractStandard.SlaProperty>()

    for (rowIndex in rolesRowIndex + 1..cellRangeAddress.lastRow) {
      val row = slaSheet.getRow(rowIndex) ?: continue

      var property: String? = null
      var value: String? = null
      var valueExt: String? = null
      var unit: String? = null
      var driver: String? = null
      var element: String? = null

      headerFields.forEach { (cellIndex, headerName) ->
        when (headerName.lowercase()) {
          "property" -> property = getCellValueAsString(row.getCell(cellIndex))
          "value" -> value = getCellValueAsString(row.getCell(cellIndex))
          "extended value" -> valueExt = getCellValueAsString(row.getCell(cellIndex))
          "unit" -> unit = getCellValueAsString(row.getCell(cellIndex))
          "driver" -> driver = getCellValueAsString(row.getCell(cellIndex))
          "element" -> element = getCellValueAsString(row.getCell(cellIndex))
        }
      }

      if (!property.isNullOrBlank()) {
        slaProperties.add(
          OpenDataContractStandard.SlaProperty(
            property = property,
            value = value,
            valueExt = valueExt,
            unit = unit,
            driver = driver,
            element = element,
          ),
        )
      }
    }
    return slaProperties


  }


  private fun importProperties(sheet: Sheet): List<OpenDataContractStandard.Property>? {
    val rows = getRowsByName(sheet, "schema.properties")

    val fieldToIndex = mutableMapOf<String, Int>()
    val headerRow = rows.firstOrNull() ?: return null
    for (cellIndex in 0 until headerRow.physicalNumberOfCells) {
      val cell = headerRow.getCell(cellIndex)
      val cellValue = getCellValueAsString(cell)
      if (!cellValue.isNullOrBlank()) {
        fieldToIndex[cellValue.lowercase().trim()] = cellIndex
      }
    }

    val propertyRows = rows.drop(1)
    val result = mutableListOf<OpenDataContractStandard.Property>()
    val lookupTable = mutableMapOf<String, OpenDataContractStandard.Property>()
    propertyRows.forEach { propertyRow ->
      val importedProperty = importProperty(propertyRow, fieldToIndex)
      if (importedProperty == null) {
        return@forEach
      }

      val name = importedProperty.name
      if (name == null) {
        return@forEach
      }

      lookupTable.put(name, importedProperty)

      if (name.contains(".")) {
        val parentPropertyName = name.substringBeforeLast(".")
        val parentProperty = lookupTable.get(parentPropertyName)

        if (parentProperty == null) {
          logger.warn("Parent property $parentPropertyName not found for $name")
          return@forEach
        }

        importedProperty.name = name.substringAfterLast(".")
        if (parentProperty.logicalType == "array") {
          parentProperty.items = importedProperty
        } else {
          parentProperty.properties = (parentProperty.properties ?: listOf()) + listOf(importedProperty)
        }
      } else {
        result.add(importedProperty)
      }
    }
    return result
  }


  private fun importProperty(
    row: Row,
    fieldToIndex: MutableMap<String, Int>
  ): OpenDataContractStandard.Property? {
    val name = getCellValueAsString(row.getCell(fieldToIndex["property"]!!))

    if (name.isNullOrBlank()) {
      return null
    }

    val authoritativeDefinitionUrl = getCellValueAsString(row.getCell(fieldToIndex["authoritative definition url"]!!))
    val authoritativeDefinitionType = getCellValueAsString(row.getCell(fieldToIndex["authoritative definition type"]!!))

    return OpenDataContractStandard.Property(
      name = name,
      primaryKey = getCellValueAsBoolean(row.getCell(fieldToIndex["primary key"]!!)),
      primaryKeyPosition = getCellValueAsInteger(row.getCell(fieldToIndex["primary key position"]!!)),
      businessName = getCellValueAsString(row.getCell(fieldToIndex["business name"]!!)),
      logicalType = getCellValueAsString(row.getCell(fieldToIndex["logical type"]!!)),
      physicalType = getCellValueAsString(row.getCell(fieldToIndex["physical type"]!!)),
      required = getCellValueAsBoolean(row.getCell(fieldToIndex["required"]!!)),
      unique = getCellValueAsBoolean(row.getCell(fieldToIndex["unique"]!!)),
      description = getCellValueAsString(row.getCell(fieldToIndex["description"]!!)),
      partitioned = getCellValueAsBoolean(row.getCell(fieldToIndex["partitioned"]!!)),
      partitionKeyPosition = getCellValueAsInteger(row.getCell(fieldToIndex["partition key position"]!!)),
      criticalDataElement = getCellValueAsBoolean(row.getCell(fieldToIndex["critical data element status"]!!)),
      tags = getCellValueAsString(row.getCell(fieldToIndex["tags"]!!))?.split(",")?.map { it.trim() },
      classification = getCellValueAsString(row.getCell(fieldToIndex["classification"]!!)),
      transformSourceObjects = getCellValueAsString(row.getCell(fieldToIndex["transform sources"]!!))?.split(",")
        ?.let { if (it.isNullOrEmpty()) null else it.map { it.trim() } },
      transformLogic = getCellValueAsString(row.getCell(fieldToIndex["transform logic"]!!)),
      transformDescription = getCellValueAsString(row.getCell(fieldToIndex["transform description"]!!)),
      examples = getCellValueAsString(row.getCell(fieldToIndex["example(s)"]!!))?.split(",")
        ?.let { if (it.isNullOrEmpty()) null else it.map { it.trim() } },
      encryptedName = getCellValueAsString(row.getCell(fieldToIndex["encrypted name"]!!)),
      authoritativeDefinitions = if (authoritativeDefinitionUrl != null && authoritativeDefinitionType != null) {
        listOf(
          OpenDataContractStandard.AuthoritativeDefinition(authoritativeDefinitionUrl, authoritativeDefinitionType),
        )
      } else {
        null
      },
      properties = null,
      quality = getCellValueAsString(row.getCell(fieldToIndex["quality description"]!!))?.let {
        listOf(
          OpenDataContractStandard.Quality(
            type = getCellValueAsString(row.getCell(fieldToIndex["quality type"]!!)) ?: "text",
            description = it,
            name = null,
            rule = null,
            unit = null,
            validValues = null,
            query = null,
            engine = null,
            implementation = null,
            dimension = null,
            method = null,
            severity = null,
            businessImpact = null,
            customProperties = null,
            authoritativeDefinitions = null,
            tags = null,
            scheduler = null,
            schedule = null,
            mustBe = null,
            mustNotBe = null,
            mustBeGreaterThan = null,
            mustBeGreaterThanOrEqualTo = null,
            mustBeLessThan = null,
            mustBeLessThanOrEqualTo = null,
            mustBeBetween = null,
            mustNotBeBetween = null,
          ),
        )
      },
      customProperties = null,
      physicalName = getCellValueAsString(row.getCell(fieldToIndex["physical name"]!!)),
      logicalTypeOptions = importLogicalTypeOptions(row, fieldToIndex),
      items = null,
    )
  }

  private fun getCellValueAsString(sheet: Sheet, columnIndex: Int, name: String): String? =
    getCellValueAsString(findCellByColumnIndex(sheet, name, columnIndex))

  private fun getCellValueAsBoolean(cell: Cell): Boolean? {
    if (cell.cellType == CellType.BLANK) {
      return null
    }

    if (cell.cellType == CellType.BOOLEAN) {
      return cell.booleanCellValue
    }

    return getCellValueAsString(cell)?.let { it.lowercase() == "true" }
  }

  private fun getCellValueAsInteger(cell: Cell): Int? {
    if (cell.cellType == CellType.BLANK) {
      return null
    }

    if (cell.cellType == CellType.NUMERIC) {
      return cell.numericCellValue.toInt()
    }

    if (cell.cellType == CellType.STRING) {
      if (cell.stringCellValue.isBlank()) {
        return null
      }
      return cell.stringCellValue.toIntOrNull()
    }

    return null
  }

  private fun getRowsByName(sheet: Sheet, name: String): List<Row> {
    val ref = nameToRef(sheet, name)
    val cellRangeAddress = CellRangeAddress.valueOf(ref)

    val rows = mutableListOf<Row>()
    for (rowIndex in cellRangeAddress.firstRow..cellRangeAddress.lastRow) {
      val row = sheet.getRow(rowIndex) ?: continue
      rows.add(row)
    }
    return rows

  }

  private fun importLogicalTypeOptions(
    row: Row,
    fieldToIndex: MutableMap<String, Int>
  ): OpenDataContractStandard.LogicalTypeOptions? {
    val result = OpenDataContractStandard.LogicalTypeOptions(
      minLength = getCellValueAsInteger(row.getCell(fieldToIndex["minimum length"]!!)),
      maxLength = getCellValueAsInteger(row.getCell(fieldToIndex["maximum length"]!!)),
      pattern = getCellValueAsString(row.getCell(fieldToIndex["pattern"]!!)),
      format = getCellValueAsString(row.getCell(fieldToIndex["format"]!!)),
      exclusiveMaximum = getCellValueAsBoolean(row.getCell(fieldToIndex["exclusive maximum"]!!)),
      exclusiveMinimum = getCellValueAsBoolean(row.getCell(fieldToIndex["exclusive minimum"]!!)),
      minimum = getCellValueAsString(row.getCell(fieldToIndex["minimum"]!!)),
      maximum = getCellValueAsString(row.getCell(fieldToIndex["maximum"]!!)),
      multipleOf = getCellValueAsString(row.getCell(fieldToIndex["multiple of"]!!)),
      minItems = getCellValueAsInteger(row.getCell(fieldToIndex["minimum items"]!!)),
      maxItems = getCellValueAsInteger(row.getCell(fieldToIndex["maximum items"]!!)),
      uniqueItems = getCellValueAsBoolean(row.getCell(fieldToIndex["unique items"]!!)),
      maxProperties = getCellValueAsInteger(row.getCell(fieldToIndex["maximum properties"]!!)),
      minProperties = getCellValueAsInteger(row.getCell(fieldToIndex["minimum properties"]!!)),
      required = getCellValueAsString(row.getCell(fieldToIndex["required properties"]!!))?.split(",")?.map { it.trim() },
    )

    if (result.minLength == null && result.maxLength == null && result.pattern == null && result.format == null &&
      result.exclusiveMaximum == null && result.exclusiveMinimum == null && result.minimum == null &&
      result.maximum == null && result.multipleOf == null && result.minItems == null && result.maxItems == null &&
      result.uniqueItems == null && result.maxProperties == null && result.minProperties == null &&
      result.required.isNullOrEmpty()) {
      return null
    }

    return result

  }

  private fun getCellValueByName(sheet: Sheet, name: String): String? {
    return getCellValueAsString(findCellByName(sheet, name))
  }

  private fun findCellByName(sheet: Sheet, name: String): Cell? {
    val ref = nameToRef(sheet, name) ?: return null
    return findCellByRef(sheet.workbook, ref)
  }

  private fun nameToRef(
    sheet: Sheet,
    name: String
  ): String? {
    val workbook = sheet.workbook
    val names = workbook.getNames(name).filter { it.sheetName == sheet.sheetName }
    if (names.isEmpty()) {
      return null
    }
    val name2 = names.first()

    return name2.refersToFormula
  }

  private fun nameToRef(
    workbook: Workbook,
    name: String
  ): String? {
    val name = workbook.getName(name)
    if (name == null) {
      return null
    }

    return name.refersToFormula
  }

  private fun findCellByRef(
    workbook: Workbook,
    cellRef: String?
  ): Cell? {
    if (cellRef == null) {
      return null
    }

    val cr = CellReference(cellRef)

    val sheetName = cr.sheetName ?: return null

    val rowIndex = cr.row
    if (rowIndex == -1) {
      return null
    }
    val colIndex = cr.col.toInt()
    if (colIndex == -1) {
      return null
    }
    val sheet = workbook.getSheet(sheetName) ?: return null
    val row = sheet.getRow(rowIndex) ?: return null
    val cell = row.getCell(colIndex) ?: return null
    return cell
  }


  private fun setCellValueByName(workbook: Workbook, cellName: String, value: Any?) {
    val cell = findCellByName(workbook, cellName)
    if (cell == null) {
      logger.warn("Cell with name $cellName not found in workbook")
      return
    }

    setCellValue(cell, value)
  }

  private fun setCellValueByName(sheet: Sheet, cellName: String, value: Any?) {
    val cell = findCellByName(sheet, cellName)
    if (cell == null) {
      logger.warn("Cell with name $cellName not found in workbook")
      return
    }

    setCellValue(cell, value)
  }

  private fun getCellValueByName(workbook: Workbook, name: String): String? {
    val cell = findCellByName(workbook, name)

    if (cell == null) {
      return null
    }

    return getCellValueAsString(cell)
  }

  private fun findCellByName(workbook: Workbook, name: String): Cell? {
    val ref = nameToRef(workbook, name) ?: return null
    return findCellByRef(workbook, ref)
  }

  private fun fillSchema(sheet: Sheet, schema: OpenDataContractStandard.Schema) {

    setCellValueByName(sheet, "schema.name", schema.name)
    setCellValueByName(sheet, "schema.physicalType", schema.physicalType)
    setCellValueByName(sheet, "schema.physicalName", schema.physicalName)
    setCellValueByName(sheet, "schema.businessName", schema.businessName)
    setCellValueByName(sheet, "schema.dataGranularityDescription", schema.dataGranularityDescription)
    setCellValueByName(sheet, "schema.description", schema.description)
    setCellValueByName(sheet, "schema.tags", schema.tags?.joinToString(","))

    fillProperties(sheet, schema.properties ?: emptyList())
  }

  private fun fillServers(workbook: Workbook, odcs: OpenDataContractStandard) {
    val sheet = workbook.getSheet("Servers") ?: return
    odcs.servers?.forEachIndexed { index, server ->

      if (server == null) return@forEachIndexed

      setCellValueByColumnIndex(sheet, "servers.server", index, server.server)
      setCellValueByColumnIndex(sheet, "servers.description", index, server.description)
      setCellValueByColumnIndex(sheet, "servers.environment", index, server.environment)
      setCellValueByColumnIndex(sheet, "servers.type", index, server.type)

      when (server.type) {
        "azure" -> {
          setCellValueByColumnIndex(sheet, "servers.azure.location", index, server.location)
          setCellValueByColumnIndex(sheet, "servers.azure.format", index, server.format)
          setCellValueByColumnIndex(sheet, "servers.azure.delimiter", index, server.delimiter)
        }

        "bigquery" -> {
          setCellValueByColumnIndex(sheet, "servers.bigquery.project", index, server.project)
          setCellValueByColumnIndex(sheet, "servers.bigquery.dataset", index, server.dataset)
        }

        "databricks" -> {
          setCellValueByColumnIndex(sheet, "servers.databricks.catalog", index, server.catalog)
          setCellValueByColumnIndex(sheet, "servers.databricks.host", index, server.host)
          setCellValueByColumnIndex(sheet, "servers.databricks.schema", index, server.schema)
        }

        "glue" -> {
          setCellValueByColumnIndex(sheet, "servers.glue.account", index, server.account)
          setCellValueByColumnIndex(sheet, "servers.glue.database", index, server.database)
          setCellValueByColumnIndex(sheet, "servers.glue.format", index, server.format)
          setCellValueByColumnIndex(sheet, "servers.glue.location", index, server.location)
        }

        "kafka" -> {
          setCellValueByColumnIndex(sheet, "servers.kafka.format", index, server.format)
          setCellValueByColumnIndex(sheet, "servers.kafka.host", index, server.host)
        }

        "postgres" -> {
          setCellValueByColumnIndex(sheet, "servers.postgres.database", index, server.database)
          setCellValueByColumnIndex(sheet, "servers.postgres.host", index, server.host)
          setCellValueByColumnIndex(sheet, "servers.postgres.port", index, server.port)
          setCellValueByColumnIndex(sheet, "servers.postgres.schema", index, server.schema)
        }

        "s3" -> {
          setCellValueByColumnIndex(sheet, "servers.s3.delimiter", index, server.delimiter)
          setCellValueByColumnIndex(sheet, "servers.s3.endpointUrl", index, server.endpointUrl)
          setCellValueByColumnIndex(sheet, "servers.s3.format", index, server.format)
          setCellValueByColumnIndex(sheet, "servers.s3.location", index, server.location)
        }

        "snowflake" -> {
          setCellValueByColumnIndex(sheet, "servers.snowflake.account", index, server.account)
          setCellValueByColumnIndex(sheet, "servers.snowflake.database", index, server.database)
          setCellValueByColumnIndex(sheet, "servers.snowflake.host", index, server.host)
          setCellValueByColumnIndex(sheet, "servers.snowflake.port", index, server.port)
          setCellValueByColumnIndex(sheet, "servers.snowflake.schema", index, server.schema)
          setCellValueByColumnIndex(sheet, "servers.snowflake.warehouse", index, server.warehouse)
        }

        "sqlserver" -> {
          setCellValueByColumnIndex(sheet, "servers.sqlserver.database", index, server.database)
          setCellValueByColumnIndex(sheet, "servers.sqlserver.host", index, server.host)
          setCellValueByColumnIndex(sheet, "servers.sqlserver.port", index, server.port)
          setCellValueByColumnIndex(sheet, "servers.sqlserver.schema", index, server.schema)
        }

        else -> {
          setCellValueByColumnIndex(sheet, "servers.custom.account", index, server.account)
          setCellValueByColumnIndex(sheet, "servers.custom.catalog", index, server.catalog)
          setCellValueByColumnIndex(sheet, "servers.custom.database", index, server.database)
          setCellValueByColumnIndex(sheet, "servers.custom.dataset", index, server.dataset)
          setCellValueByColumnIndex(sheet, "servers.custom.delimiter", index, server.delimiter)
          setCellValueByColumnIndex(sheet, "servers.custom.endpointUrl", index, server.endpointUrl)
          setCellValueByColumnIndex(sheet, "servers.custom.format", index, server.format)
          setCellValueByColumnIndex(sheet, "servers.custom.host", index, server.host)
          setCellValueByColumnIndex(sheet, "servers.custom.location", index, server.location)
          setCellValueByColumnIndex(sheet, "servers.custom.path", index, server.path)
          setCellValueByColumnIndex(sheet, "servers.custom.port", index, server.port)
          setCellValueByColumnIndex(sheet, "servers.custom.project", index, server.project)
          setCellValueByColumnIndex(sheet, "servers.custom.region", index, server.region)
          setCellValueByColumnIndex(sheet, "servers.custom.regionName", index, server.regionName)
          setCellValueByColumnIndex(sheet, "servers.custom.schema", index, server.schema)
          setCellValueByColumnIndex(sheet, "servers.custom.serviceName", index, server.serviceName)
          setCellValueByColumnIndex(sheet, "servers.custom.stagingDir", index, server.stagingDir)
          setCellValueByColumnIndex(sheet, "servers.custom.table", index, server.table)
          setCellValueByColumnIndex(sheet, "servers.custom.view", index, server.view)
          setCellValueByColumnIndex(sheet, "servers.custom.warehouse", index, server.warehouse)
        }
      }
    }
  }

  private fun setCellValueByColumnIndex(
    sheet: Sheet,
    name: String,
    columnIndex: Int,
    value: String?
  ) {
    findCellByColumnIndex(sheet, name, columnIndex)?.setCellValue(value)
  }

  private fun findCellByColumnIndex(
    sheet: Sheet,
    name: String,
    columnIndex: Int,
  ): Cell? {
    val firstCell = findCellByName(sheet, name) ?: return null
    val row = firstCell.row ?: return null
    val columnIndex = firstCell.columnIndex.plus(columnIndex)
    return row.getCell(columnIndex)
  }

  private fun fillProperties(sheet: Sheet, properties: List<OpenDataContractStandard.Property>, prefix: String = "") {

    val ref = nameToRef(sheet, "schema.properties") ?: throw RuntimeException("No schema.properties found")
    val cellRangeAddress = CellRangeAddress.valueOf(ref)

    // find row index with a cell value Property
    val propertiesHeaderRowIndex = cellRangeAddress.firstRow

    val headers = getHeadersFromHeaderRow(sheet, propertiesHeaderRowIndex)

    // For each property, add a row with its information
    var rowIndex = propertiesHeaderRowIndex + 1 // Start after header row
    properties.forEach { property ->
      // copy row at rowIndex
      rowIndex = rowIndex + fillProperty(sheet, rowIndex, headers, prefix, property)
    }
  }

  private fun fillProperty(
    sheet: Sheet,
    rowIndex: Int,
    headers: Map<Int, String>,
    prefix: String,
    property: OpenDataContractStandard.Property
  ): Int {
    val row = sheet.getRow(rowIndex)

    headers.forEach { (cellIndex, headerName) ->
      when (headerName.lowercase()) {
        "property" -> setCellValue(row, cellIndex, prefix + property.name)
        "business name" -> setCellValue(row, cellIndex, property.businessName)
        "logical type" -> setCellValue(row, cellIndex, property.logicalType)
        "physical type" -> setCellValue(row, cellIndex, property.physicalType)
        "physical name" -> setCellValue(row, cellIndex, property.physicalName)
        "example(s)" -> setCellValue(row, cellIndex, property.examples?.joinToString(","))
        "description" -> setCellValue(row, cellIndex, property.description)
        "required" -> setCellValue(row, cellIndex, property.required)
        "unique" -> setCellValue(row, cellIndex, property.unique)
        "classification" -> setCellValue(row, cellIndex, property.classification)
        "tags" -> setCellValue(row, cellIndex, property.tags?.joinToString(","))
        "quality type" -> setCellValue(row, cellIndex, property.quality?.firstOrNull()?.type)
        "quality description" -> setCellValue(row, cellIndex, property.quality?.firstOrNull()?.description)
        "authoritative definition url" -> setCellValue(row, cellIndex, property.authoritativeDefinitions?.firstOrNull()?.url)
        "authoritative definition type" -> setCellValue(row, cellIndex, property.authoritativeDefinitions?.firstOrNull()?.type)
        "primary key" -> setCellValue(row, cellIndex, property.primaryKey)
        "primary key position" -> setCellValue(row, cellIndex, property.primaryKeyPosition)
        "partitioned" -> setCellValue(row, cellIndex, property.partitioned)
        "partition key position" -> setCellValue(row, cellIndex, property.partitionKeyPosition)
        "encrypted name" -> setCellValue(row, cellIndex, property.encryptedName)
        "transform sources" -> setCellValue(row, cellIndex, property.transformSourceObjects?.joinToString(","))
        "transform logic" -> setCellValue(row, cellIndex, property.transformLogic)
        "transform description" -> setCellValue(row, cellIndex, property.transformDescription)
        "critical data element status" -> setCellValue(row, cellIndex, property.criticalDataElement)
        "minimum items" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.minItems)
        "maximum items" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.maxItems)
        "unique items" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.uniqueItems)
        "format" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.format)
        "minimum length" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.minLength)
        "maximum length" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.maxLength)
        "exclusive minimum" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.exclusiveMinimum)
        "exclusive maximum" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.exclusiveMaximum)
        "minimum" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.minimum)
        "maximum" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.maximum)
        "multiple of" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.multipleOf)
        "minimum properties" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.minProperties)
        "maximum properties" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.maxProperties)
        "required properties" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.required?.joinToString(","))
        "pattern" -> setCellValue(row, cellIndex, property.logicalTypeOptions?.pattern)
      }
    }

    if (property.items != null) {
      var result = 1

      val items = property.items!!
      result += fillProperty(
        sheet = sheet,
        rowIndex = rowIndex + result,
        prefix = prefix + "${property.name}.",
        headers = headers,
        property = items,
      )

      return result
    } else if (property.properties != null) {
      var result = 1

      val subProperties = property.properties!!
      subProperties.forEach {
        result += fillProperty(
          sheet = sheet,
          rowIndex = rowIndex + result,
          prefix = prefix + "${property.name}.",
          headers = headers,
          property = it,
        )
      }
      return result
    } else {
      return 1
    }
  }

  // Helper method to get headers from the first row
  private fun getHeadersFromHeaderRow(sheet: Sheet, headerRowIndex: Int): Map<Int, String> {
    val headers = mutableMapOf<Int, String>()
    val headerRow = sheet.getRow(headerRowIndex) ?: return headers

    for (cellIndex in 0 until headerRow.physicalNumberOfCells) {
      val cell = headerRow.getCell(cellIndex)
      val value = getCellValueAsString(cell)
      if (!value.isNullOrBlank()) {
        headers[cellIndex] = value
      }
    }
    return headers
  }

  private fun parsePropertyValue(valueCell: Cell?): Any? {
    if (valueCell == null) {
      return null
    }

    return when (valueCell.cellType) {
      CellType.BLANK -> null
      CellType.NUMERIC -> valueCell.numericCellValue
      CellType.BOOLEAN -> valueCell.booleanCellValue
      CellType.STRING -> {
        val value = valueCell.stringCellValue
        when {
          value.startsWith("{") -> objectMapper.readValue(value, Any::class.java)
          value.startsWith("[") -> objectMapper.readValue(value, List::class.java)
          else -> value
        }
      }
      else -> getCellValueAsString(valueCell)
    }
  }

  private fun setCellValue(row: Row, cellIndex: Int, value: Any?) {
    val cell = getOrCreateCell(row, cellIndex)
    setCellValue(cell, value)
  }

  private fun setCellValue(cell: Cell, value: Any?) {
    if (value != null) {
      when (value) {
        is String -> if (value.isBlank()) {
          cell.setBlank()
        } else {
          cell.setCellValue(value)
        }

        is Double -> cell.setCellValue(value)
        is Boolean -> cell.setCellValue(value)
        else -> cell.setCellValue(value.toString())
      }
    } else {
      cell.setBlank()
    }
  }

  // Helper method to set cell values
  private fun setCellValue(row: Row, cellIndex: Int, value: String?) {
    val cell = getOrCreateCell(row, cellIndex)
    setCellValue(cell, value)
  }

  private fun setCellValue(row: Row, cellIndex: Int, value: Double?) {
    val cell = getOrCreateCell(row, cellIndex)
    setCellValue(cell, value)
  }

  private fun setCellValue(row: Row, cellIndex: Int, value: Boolean?) {
    val cell = getOrCreateCell(row, cellIndex)
    setCellValue(cell, value)
  }

  private fun getOrCreateCell(row: Row, cellIndex: Int): Cell = row.getCell(cellIndex) ?: row.createCell(cellIndex)

  // Helper method to get cell value as string
  private fun getCellValueAsString(cell: Cell?): String? {
    if (cell == null) return null

    return when (cell.cellType) {
      CellType.BLANK -> null
      CellType.STRING -> cell.stringCellValue.takeIf { it.isNotBlank() }
      CellType.NUMERIC -> cell.numericCellValue.toString()
      CellType.BOOLEAN -> cell.booleanCellValue.toString()
      CellType.FORMULA -> {
        try {
          when (cell.cachedFormulaResultType) {
            CellType.STRING -> cell.stringCellValue.takeIf { it.isNotBlank() }
            CellType.NUMERIC -> cell.numericCellValue.toString()
            CellType.BOOLEAN -> cell.booleanCellValue.toString()
            else -> null
          }
        } catch (e: Exception) {
          null
        }
      }

      else -> null
    }
  }


}
