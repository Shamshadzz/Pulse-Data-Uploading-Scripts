namespace CCTECH.DRS.ENTITIES;

///////////////////////////////////////////////////
// ENUM TYPES
///////////////////////////////////////////////////

type project_category          : String enum {
  ppa;
  captive;
  epc;
  merchant;
}

type assignee_type             : String enum {
  CONTRACTOR;
  ENGINEER;
  QUALITY;
}

type package_type              : String enum {
  civil;
  electrical;
  mechanical;
}

type auth_type                 : String enum {
  local;
  adfs;
}

type rfi_status                : String enum {
  draft;
  submitted;
  rejected;
  approved;
  completed
}

type rfi_handlers              : String enum {
  contractor;
  block_engineer;
  quality_inspector;
}

type nc_status                 : String enum {
  draft;
  submitted;
  rejected;
  approved;
  completed;
}

type checklist_response_status : String enum {
  ok;
  not_ok;
}

///////////////////////////////////////////////////
// MASTER DATA / REFERENCE
///////////////////////////////////////////////////

@assert.unique: {unique_uom: [CODE]}
entity UNITOFMEASURES {
  key ID          : UUID;
      CODE        : String; // e.g. 'M','M2','EA'
      DESCRIPTION : String;

// --- seed values from SAP UOM catalog ---
// ('M',    'Meter')
// ('M2',   'Square Meter')
// ('M3',   'Cubic Meter')
// ('MT',   'Metric Ton')
// ('EA',   'Each / Unit')
// ('NO',   'Number of items')
// ('LSM',  'Lump Sum')
}

@assert.unique: {unique_cluster: [NAME]}
entity CLUSTERS {
  key ID   : UUID;
      NAME : String; // eg: KHAVDA
}

@assert.unique: {unique_cluster: [
  CLUSTER_ID,
  NAME
]}
entity LOCATIONS {
  key ID         : UUID;
      CLUSTER_ID : UUID;
      NAME       : String; // eg: KACHCHH
}

@assert.unique: {unique_cluster: [
  LOCATION_ID,
  NAME
]}
entity PLOTS {
  key ID                : UUID;
      LOCATION_ID       : UUID;
      NAME              : String; // eg: KACHCHH
      DESIGN_ELEMENT_ID : UUID; // eg: KACHCHH
}

@assert.unique: {unique_cluster: [NAME]}
entity SPVS {
  key ID   : UUID;
      NAME : String;
}

entity PROJECTS {
  key ID        : UUID;
      SPV_ID    : UUID;
      SPV       : Association to SPVS
                    on SPV.ID = $self.SPV_ID;
      NAME      : String;
      TYPE      : String;
      CATEGORY  : String;
      RFI_COUNT : Integer;
      NC_COUNT  : Integer;
}

entity DESIGNELEMENTS {
  key ID         : UUID;
      PROJECT_ID : UUID;
      PROJECT    : Association to PROJECTS
                     on PROJECT.ID = $self.PROJECT_ID;
      NAME       : String;
      TYPE       : String; // plot, block, table, inverter, ...
      PARENT_ID  : UUID;
      PARENT     : Association to DESIGNELEMENTS
                     on PARENT.ID = $self.PARENT_ID;

// Notes:
// - Unifies plot, block, table_unit, inverter under one entity.
// - Allows future expansion
// - Enables hierarchy traversal via parent_id.
// - eg:
//     P1 (type=plot)
//     B1 (type=block, parent=P1)
//     T1 (type=table, parent=B1)
//     INV1 (type=inverter, parent=B1)
}

@assert.unique: {unique_vendor: [CODE]}
entity VENDORS {
  key ID         : UUID;
      CODE       : String; // SAP vendor code
      NAME       : String; // Vendor name from SAP
      GST_NUMBER : String; // GSTIN of the vendor/contractor
}

///////////////////////////////////////////////////////////////////////
// WBS / SERVICE ORDER / PROJECT DEFINITION / SOLAR PROJECT ATTRIBUTES
///////////////////////////////////////////////////////////////////////

@assert.unique: {unique_wbs_element: [CODE]}
entity WBSELEMENTS {
  key ID                    : UUID;
      PROJECT_ID            : UUID;
      PROJECT               : Association to PROJECTS
                                on PROJECT.ID = $self.PROJECT_ID;
      PROJECT_DEFINITION_ID : UUID;
      PROJECTDEFINITION     : Association to PROJECTDEFINITIONS
                                on PROJECTDEFINITION.ID = $self.PROJECT_DEFINITION_ID;
      PARENT_ID             : UUID;
      PARENT                : Association to WBSELEMENTS
                                on PARENT.ID = $self.PARENT_ID;
      CODE                  : String; // eg: H-623Z-05-08
      DESCRIPTION           : String;
}

@assert.unique: {unique_serviceorders_plot: [
  SERVICEORDER_ID,
  PLOT_ID
]}
entity SERVICEORDERPLOTS {
  key ID              : UUID;
      SERVICEORDER_ID : UUID;
      PLOT_ID      : UUID;
}

@assert.unique: {unique_serviceorders_package: [
  SERVICEORDER_ID,
  PACKAGE_ID
]}
entity SERVICEORDERPACKAGES {
  key ID              : UUID;
      SERVICEORDER_ID : UUID;
      PACKAGE_ID      : UUID;
}

@assert.unique: {unique_serviceorders_package: [
  VENDOR_ID,
  BLOCK_ID,
  ACTIVITY_ID,
]}
entity SERVICEORDERBLOCKS {
  key ID              : UUID;
      SERVICEORDER_ID : UUID;
      VENDOR_ID       : UUID;
      PLOT_ID         : UUID;
      BLOCK_ID        : UUID;
      PACKAGE_ID      :UUID;
      ACTIVITY_ID     : UUID;
}

@assert.unique: {unique_service_order: [SO_NUMBER]}
entity SERVICEORDERS {
  key ID                    : UUID;
      SO_NUMBER             : String; // eg: 4810023149

      PROJECT_ID            : UUID; // service order belongs to a project
      PROJECT               : Association to PROJECTS
                                on PROJECT.ID = $self.PROJECT_ID;

      PROJECT_DEFINITION_ID : UUID;
      PROJECT_DEFINITION    : Association to PROJECTDEFINITIONS
                                on PROJECT_DEFINITION.ID = $self.PROJECT_DEFINITION_ID;
      VENDOR_ID             : UUID;
      VENDOR                : Association to VENDORS
                                on VENDOR.ID = $self.VENDOR_ID;

      HEADER_TEXT           : String;
      DATE                  : Timestamp;
}

@assert.unique: {unique_project_definition: [CODE]}
entity PROJECTDEFINITIONS {
  key ID            : UUID;
      PROJECT_ID    : UUID;
      PROJECT       : Association to PROJECTS
                        on PROJECT.ID = $self.PROJECT_ID;
      CODE          : String;
      DESCRIPTION   : String;
      SYSTEM_STATUS : String;
      BUSINESS_AREA : String;
}

@assert.unique: {unique_solar_project_attribute: [PROJECT_ID]}
entity SOLARPROJECTATTRIBUTES {
  key ID               : UUID;
      PROJECT_ID       : UUID;
      PROJECT          : Association to PROJECTS
                           on PROJECT.ID = $self.PROJECT_ID;
      MMS_TYPE         : String;
      CAPACITY         : Decimal(18, 6);
      PSS_CONNECTED_ID : UUID;
      PSS_CONNECTED    : Association to DESIGNELEMENTS
                           on PSS_CONNECTED.ID = $self.PSS_CONNECTED_ID;
}

///////////////////////////////////////////////////
// PACKAGE / SUB-PACKAGE / ACTIVITY HIERARCHY
///////////////////////////////////////////////////

entity PACKAGES {
  key ID   : UUID;
      NAME : String;

// Notes:
// - Represents top-level engineering discipline.
}

@assert.unique: {unique_sub_package: [CODE]}
entity SUBPACKAGES {
  key ID         : UUID;
      PACKAGE_ID : UUID;
      PACKAGE    : Association to PACKAGES
                     on PACKAGE.ID = $self.PACKAGE_ID;
      NAME       : String;
      CODE       : String;

// Notes:
// - Logical subdivision of a package.
// - eg: “Piling + IDT Civil & Structural”
// - Each sub-package can contain multiple activities.
}

@assert.unique: {unique_activity: [CODE]}
entity ACTIVITIES {
  key ID             : UUID;
      SUB_PACKAGE_ID : UUID;
      SUBPACKAGE     : Association to SUBPACKAGES
                         on SUBPACKAGE.ID = $self.SUB_PACKAGE_ID;
      NAME           : String;
      CODE           : String;
      BASE_UOM       : String;
}

@assert.unique: {unique_sub_activity: [CODE]}
entity SUBACTIVITY {
  key ID                 : UUID;
      ACTIVITY_ID        : UUID;
      ACTIVITY           : Association to ACTIVITIES
                             on ACTIVITY.ID = $self.ACTIVITY_ID;
      NAME               : String;
      MIN_UNIT           : String;
      UNIT_OF_MEASURE_ID : UUID;
      UNITOFMEASURE      : Association to UNITOFMEASURES
                             on UNITOFMEASURE.ID = $self.UNIT_OF_MEASURE_ID;
      CODE               : String;

// Notes:
// - eg: “Piling - For MMS”, “Cable Laying - HT Side”
}

///////////////////////////////////////////////////
// PERSONNEL & AUTH
///////////////////////////////////////////////////

@assert.unique: {unique_personnel_email: [EMAIL]}
entity PERSONNELS {
  key ID          : UUID;
      NAME        : String;
      EMAIL       : String;
      PHONE       : String;
      ROLE        : Association to ROLES;
      ACTIVE      : Boolean;
      AUTH_TYPE   : auth_type; // enum: local for contractors, adfs for internal SSO
      EXTERNAL_ID : String;
      MANAGER_ID  : UUID; // hierarchy
      MANAGER     : Association to PERSONNELS
                      on MANAGER.ID = $self.MANAGER_ID;
      VENDOR_ID   : UUID; // only relevant for contractor_manager
      VENDOR      : Association to VENDORS
                      on VENDOR.ID = $self.VENDOR_ID;
      CLUSTER     : Association to CLUSTERS;
      LOCATION    : Association to LOCATIONS
// Notes(Personnel & Roles):
// 1. auth_type = easy to extend for future auth types
// 2. Multi level Hierarchy supported via 'manager_id'
//        - contractor Manager → role=contractor_manager
//        - contractor In-charge → role=contractor_in_charge, manager_id = contractor_manager.id
//        - quality Lead → role=quality_lead
//        - quality inspector → role=quality_inspector, manager_id = quality_lead.id
//        - site Head → role=site_head, oversees plots
// 3. flexible region assignments (Each personnel can have multiple blocks or plots assigned)
}

// ---------
// Roles
// ---------
entity ROLES {
  key ID          : UUID;
      NAME        : String; // eg:  "quality_lead"
      DESCRIPTION : String;
}

// ----------------------------------
// Grants (Role-based permissions)
// ----------------------------------
entity GRANTS {
  key ID         : UUID;
      ROLE       : Association to ROLES;
      RESOURCE   : String;
      ACTION     : String;
      ATTRIBUTES : String;
      DELETEDAT  : Timestamp;
}

entity USERAUTH {
  key ID            : UUID;
      PERSONNEL_ID  : UUID;
      PERSONNEL     : Association to PERSONNELS
                        on PERSONNEL.ID = $self.PERSONNEL_ID;
      PASSWORD_HASH : String;
      SALT          : String;
      CREATED_AT    : Timestamp;
      UPDATED_AT    : Timestamp;

// Notes:
// - Only required for auth_type = local
// - ADFS users authenticate via external_id (SSO), no password stored
}

entity SESSIONS {
  key ID           : String;
      VALUE        : LargeString;
      SECONDSTOKEN : String;
      TTL_SECONDS  : Timestamp;
}

///////////////////////////////////////////////////
// RFI CORE
///////////////////////////////////////////////////

entity RFIS {
  key ID                               : UUID;

      CONTRACTOR_ID                    : UUID;
      CONTRACTOR                       : Association to PERSONNELS
                                           on CONTRACTOR.ID = $self.CONTRACTOR_ID;
      ENGINEER_ID                      : UUID;
      ENGINEER                         : Association to PERSONNELS
                                           on ENGINEER.ID = $self.ENGINEER_ID;
      QUALITY_ID                       : UUID;
      QUALITY                          : Association to PERSONNELS
                                           on QUALITY.ID = $self.QUALITY_ID;
      SERVICE_ORDER_ID                 : UUID;
      SERVICE_ORDER                    : Association to SERVICEORDERS
                                           on SERVICE_ORDER.ID = $self.SERVICE_ORDER_ID;

      INSPECTION_POINT_ID              : UUID;
      INSPECTION_POINT                 : Association to INSPECTION_POINTS
                                           on INSPECTION_POINT.ID = $self.INSPECTION_POINT_ID;
      CHECKLIST_ID                     : UUID;
      CHECKLIST                        : Association to CHECKLISTS
                                           on CHECKLIST.ID = $self.CHECKLIST_ID;

      PROJECT_ID                       : UUID;
      PROJECT                          : Association to PROJECTS
                                           on PROJECT.ID = $self.PROJECT_ID;

      BLOCK_ID         : UUID;
      DESIGNELEMENT    : Association to DESIGNELEMENTS
                           on DESIGNELEMENT.ID = $self.BLOCK_ID;


      PLOT_ID         : UUID;


      PACKAGE_ID        : UUID;
      PACKAGE           : Association to PACKAGES
                            on PACKAGE.ID = $self.PACKAGE_ID;

      VERSION                          : Integer;
      PARENT_ID                        : UUID;
      PARENT                           : Association to RFIS
                                           on PARENT.ID = $self.PARENT_ID;
      ROOT_ID                          : UUID;
      ROOT                             : Association to RFIS
                                           on ROOT.ID = $self.ROOT_ID;

      RFI_LABEL                        : String;
      ARCHIVED                         : Boolean;
      STATUS                           : rfi_status;
      OVERALL_REMARKS                  : String;
      LAST_REVIEWED_BY_ID              : UUID;
      LAST_REVIEWED_BY                 : Association to PERSONNELS
                                           on LAST_REVIEWED_BY.ID = $self.LAST_REVIEWED_BY_ID;
      CREATED_AT                       : Timestamp;
      UPDATED_AT                       : Timestamp;
      CURRENT_HANDLER                  : rfi_handlers;
      SUB_CONTRACTOR_NAME              : String;

      DEBIT                            : Integer;
      QUANTITY                         : Decimal;
      UOM                              : String;
      INSPECTION_CHECK_NOT_REQUIRED    : Boolean;
      BE_INSPECTION_CHECK_NOT_REQUIRED : Boolean;
      QI_INSPECTION_CHECK_NOT_REQUIRED : Boolean;

// Notes:
// - versioning supports RFI v1, v2, etc. if rejected
// - status + current_assignee_id track workflow state
}

///////////////////////////////////////////////////
// UNIT SCOPE (unified)
///////////////////////////////////////////////////
entity UNITSCOPE {
  key ID                : UUID;
      RFI_ID            : UUID;
      RFI               : Association to RFIS
                            on RFI.ID = $self.RFI_ID;
      NC_ID             : UUID;
      NC                : Association to NCS
                            on NC.ID = $self.NC_ID;
      DESIGN_ELEMENT_ID : UUID;
      DESIGNELEMENT     : Association to DESIGNELEMENTS
                            on DESIGNELEMENT.ID = $self.DESIGN_ELEMENT_ID;

// Notes:
// - Scope can point to any design element level (plot/block/table/inverter/etc.).
// - Enforce XOR rule:
//      (rfi_id IS NOT NULL AND nc_id IS NULL)
//   OR (rfi_id IS NULL AND nc_id IS NOT NULL)
}

///////////////////////////////////////////////////
// RFI CHECKLIST RESPONSES
///////////////////////////////////////////////////
entity RFICHECKLISTRESPONSE {
  key ID                    : UUID;
      RFI_ID                : UUID;
      RFI                   : Association to RFIS
                                on RFI.ID = $self.RFI_ID;
      CHECKLIST_QUESTION_ID : UUID;
      CHECKLISTQUESTION     : Association to CHECKLISTQUESTIONS
                                on CHECKLISTQUESTION.ID = $self.CHECKLIST_QUESTION_ID;
      PERSONNEL_ID          : UUID;
      PERSONNEL             : Association to PERSONNELS
                                on PERSONNEL.ID = $self.PERSONNEL_ID;
      ROLE_AT_TIME          : rfi_handlers;
      REMARKS               : String;
      STATUS                : checklist_response_status;
      RESPONDED_AT          : Timestamp;
      LINKED_NC_ID          : UUID;
      LINKED_NC             : Association to NCS
                                on LINKED_NC.ID = $self.LINKED_NC_ID;

// Notes:
// - Tracks who responded to each checkpoint
// - Supports remarks, status, and attachments per role
}

///////////////////////////////////////////////////
// NC CORE
///////////////////////////////////////////////////

entity NCS {
  key ID                        : UUID;
      QUALITY_ID                : UUID;
      QUALITY                   : Association to PERSONNELS
                                    on QUALITY.ID = $self.QUALITY_ID;

      ENGINEER_ID               : UUID;
      ENGINEER                  : Association to PERSONNELS
                                    on ENGINEER.ID = $self.ENGINEER_ID;

      CONTRACTOR_ID             : UUID;
      CONTRACTOR                : Association to PERSONNELS
                                    on CONTRACTOR.ID = $self.CONTRACTOR_ID;
      SERVICE_ORDER_ID          : UUID;
      SERVICE_ORDER             : Association to SERVICEORDERS
                                    on SERVICE_ORDER.ID = $self.SERVICE_ORDER_ID;


      BLOCK_ID         : UUID;
      DESIGNELEMENT    : Association to DESIGNELEMENTS
                           on DESIGNELEMENT.ID = $self.BLOCK_ID;


      PLOT_ID         : UUID;


      PACKAGE_ID        : UUID;
      PACKAGE           : Association to PACKAGES
                            on PACKAGE.ID = $self.PACKAGE_ID;

      RFI_CHECKLIST_RESPONSE_ID : UUID;
      RFICHECKLISTRESPONSE      : Association to RFICHECKLISTRESPONSE
                                    on RFICHECKLISTRESPONSE.ID = $self.RFI_CHECKLIST_RESPONSE_ID;

      SUBACTIVITY_ID            : UUID;
      SUBACTIVITY               : Association to SUBACTIVITY
                                    on SUBACTIVITY.ID = $self.SUBACTIVITY_ID;
      PARENT_ID                 : UUID;
      PARENT                    : Association to NCS
                                    on PARENT.ID = $self.PARENT_ID;
      ROOT_ID                   : UUID;
      ROOT                      : Association to NCS
                                    on ROOT.ID = $self.ROOT_ID;
      NC_LABEL                  : String;
      ARCHIVED                  : Boolean;
      VERSION                   : Integer;
      AD_HOC                    : Boolean;
      DESCRIPTION               : String;
      DEFECT_TYPE               : String;
      CATEGORY                  : String;
      DEBIT                     : Integer;
      DEBIT_REASON              : String;
      STATUS                    : nc_status;
      CURRENT_HANDLER           : rfi_handlers;
      QUANTITY                  : Integer;
      UNIT_OF_MEASUREMENT       : String;
      CREATED_AT                : Timestamp;
      UPDATED_AT                : Timestamp;
// Todo Change the name UNIT_OF_MEASURMENT to UOM  or change the corresponding fields name in rfi
// Notes:
// - If ad_hoc = false → linked to a specific RFI checklist response
// - If ad_hoc = true  → standalone NC
}

entity NCRESPONSES {
  key ID                 : UUID;
      NC_ID              : UUID;
      NC                 : Association to NCS
                             on NC.ID = $self.NC_ID;
      CONTRACTOR_ID      : UUID;
      CONTRACTOR         : Association to PERSONNELS
                             on CONTRACTOR.ID = $self.CONTRACTOR_ID;

      PERSONNEL_ID       : UUID;
      PERSONNEL          : Association to PERSONNELS
                             on PERSONNEL.ID = $self.PERSONNEL_ID;


      ROLE_AT_TIME       : rfi_handlers;
      STATUS             : checklist_response_status;
      REMARKS            : String;
      ROOT_CAUSE         : String;
      CORRECTIVE_ACTIONS : String;
      SUBMITTED_AT       : Timestamp;
}

entity NCASSIGNEES {
  key ID            : UUID;
      NC_ID         : UUID;
      NC            : Association to NCS
                        on NC.ID = $self.NC_ID;
      PERSONNEL_ID  : UUID;
      PERSONNEL     : Association to PERSONNELS
                        on PERSONNEL.ID = $self.PERSONNEL_ID;
      ROLE_AT_TIME  : String;
      ASSIGNED_AT   : Timestamp;
      UNASSIGNED_AT : Timestamp;
}

///////////////////////////////////////////////////
// CHECKLIST MASTER / QUESTIONS
///////////////////////////////////////////////////

@assert.unique: {unique_inspection_point: [
  SUB_ACTIVITY_ID,
  SERIAL
]}
entity INSPECTION_POINTS {
  key ID                           : UUID;
      SERIAL                       : String;
      SUB_ACTIVITY_ID              : UUID;
      SUBACTIVITY                  : Association to SUBACTIVITY
                                       on SUBACTIVITY.ID = $self.SUB_ACTIVITY_ID;
      VARIANT                      : String;
      TYPE                         : String;
      OPTIONAL                     : Boolean;
      INSPECTION_POINT_NAME        : String;
      INSPECTION_POINT_DESCRIPTION : String;
}

entity CHECKLISTS {
  key ID             : UUID;
      SERIAL         : String;
      CHECKLIST_NAME : String;
      SFQP_NUMBER    : String;
      FORMAT_NUMBER  : String;
}

entity INSPECTION_POINTS_DEPENDENCIES {
  key ID        : UUID;
      PARENT_ID : UUID;
      PARENT    : Association to INSPECTION_POINTS
                    on PARENT.ID = $self.PARENT_ID;
      CHILD_ID  : UUID;
      CHILD     : Association to INSPECTION_POINTS
                    on CHILD.ID = $self.CHILD_ID;
}

entity CHECKLISTQUESTIONS {
  key ID                : UUID;
      CHECKLIST_ID      : UUID;
      QUESTION_NUMBER   : Integer;
      QUESTION_TEXT     : String;
      INPUT_TYPE        : String;
      IS_VALUE_REQUIRED : Boolean;
      OPTIONAL          : Boolean;
      ACTIVE            : Boolean;
      CREATED_AT        : Timestamp;
      UPDATED_AT        : Timestamp;
}


// Juntion Table to connect Inspection Point and Checklist
entity INSPECTION_POINTS_TO_CHECKLIST {
  key ID                  : UUID;
      INSPECTION_POINT_ID : UUID;
      CHECKLIST_ID        : UUID;
}

////////////////////////////////
// UNIFIED AUDIT LOG
////////////////////////////////
entity AUDITLOGS {
  key ID           : Integer64;
      COMMAND_ID   : String;
      ENTITY_TYPE  : String; // 'rfi','nc','wmc',...
      ENTITY_ID    : UUID;
      ACTION       : String; // create, update, delete
      EVENT        : String; // Submitted, Draft, etc.
      PAYLOAD      : String;
      PERFORMED_BY : UUID;
      PERFORMEDBY  : Association to PERSONNELS
                       on PERFORMEDBY.ID = $self.PERFORMED_BY;
      TIMESTAMP    : Timestamp;
}

//////////////////////////////
// RFI ASSIGNEES
//////////////////////////////
entity RFIASSIGNEES {
  key ID            : UUID;
      RFI_ID        : UUID;
      RFI           : Association to RFIS
                        on RFI.ID = $self.RFI_ID;
      PERSONNEL_ID  : UUID;
      PERSONNEL     : Association to PERSONNELS
                        on PERSONNEL.ID = $self.PERSONNEL_ID;
      ROLE_AT_TIME  : String;
      ASSIGNED_AT   : Timestamp;
      UNASSIGNED_AT : Timestamp;
}

///////////////////////////////////
// PERSONNEL REGION ASSIGNMENT
///////////////////////////////////
entity PERSONNELREGIONASSIGNMENTS {
  key ID                : UUID;
      PERSONNEL_ID      : UUID;
      PERSONNEL         : Association to PERSONNELS
                            on PERSONNEL.ID = $self.PERSONNEL_ID;
      ROLE_ID           : UUID;
      ROLE              : Association to ROLES
                            on ROLE.ID = $self.ROLE_ID;
      DESIGN_ELEMENT_ID : UUID;
      DESIGNELEMENT     : Association to DESIGNELEMENTS
                            on DESIGNELEMENT.ID = $self.DESIGN_ELEMENT_ID;

      PACKAGE_ID        : UUID;
      PACKAGE           : Association to PACKAGES
                            on PACKAGE.ID = $self.PACKAGE_ID;

      ASSIGNED_AT       : Timestamp;
      UNASSIGNED_AT     : Timestamp;
}

////////////////////////////////////
// WORK MEASUREMENT CERTIFICATE
////////////////////////////////////

entity WMCS {
  key ID               : UUID;
      SERVICE_ORDER_ID : UUID;
      SERVICE_ORDER    : Association to SERVICEORDERS
                           on SERVICE_ORDER.ID = $self.SERVICE_ORDER_ID;
      GENERATED_BY_ID  : UUID;
      GENERATEDBY      : Association to PERSONNELS
                           on GENERATEDBY.ID = $self.GENERATED_BY_ID;

      BLOCK_ID         : UUID;
      DESIGNELEMENT    : Association to DESIGNELEMENTS
                           on DESIGNELEMENT.ID = $self.BLOCK_ID;
      PACKAGE_ID       : UUID;
      PACKAGE          : Association to PACKAGES
                           on PACKAGE.ID = $self.PACKAGE_ID;
      CREATED_AT       : Timestamp;
      WMC_LABEL        : String;
      WMC_FILE_URL     : String;
}

entity WMCWORKSCOPES {
  key ID                   : UUID;
      WMC_ID               : UUID;
      WMC                  : Association to WMCS
                               on WMC.ID = $self.WMC_ID;
      ACTIVITY_ID          : UUID;
      ACTIVITY             : Association to ACTIVITIES
                               on ACTIVITY.ID = $self.ACTIVITY_ID;
      LAST_RFI_APPROVED_AT : Timestamp;
      TOTAL_DEBIT          : Integer;
}


entity SYSTEM_META {
  key ID    : UUID;

      // e.g. start time
      NAME  : String;
      VALUE : String;
}

entity FILES {
  key ID         : UUID;
      NAME       : String;
      MIME       : String;
      BLOB       : LargeBinary;
      SIZE       : Integer64;
      VERSION    : Integer;
      LATITUDE   : Decimal;
      LONGITUDE  : Decimal;
      CREATED_AT : Timestamp;
      UPDATED_AT : Timestamp;
}

entity RFI_ATTACHMENTS {
  key ID            : UUID;
      RFI_ID        : UUID;
      RFI           : Association to RFIS
                        on RFI.ID = $self.RFI_ID;
      ATTACHMENT_ID : UUID;
      FILES         : Association to FILES
                        on FILES.ID = $self.ATTACHMENT_ID
}

entity CHECKLISTRESPONSEATTACHMENT {
  key ID                   : UUID;
      RESPONSE_ID          : UUID;
      RFICHECKLISTRESPONSE : Association to RFICHECKLISTRESPONSE
                               on RFICHECKLISTRESPONSE.ID = $self.RESPONSE_ID;

      FILE_ID              : UUID;
      FILES                : Association to FILES
                               on FILES.ID = $self.FILE_ID;

      LOCATION_LAT         : Decimal;
      LOCATION_LNG         : Decimal;
}

entity NC_ATTACHMENTS {
  key ID            : UUID;
      NC_ID         : UUID;
      NC            : Association to NCS
                        on NC.ID = $self.NC_ID;
      ATTACHMENT_ID : UUID;
      FILES         : Association to FILES
                        on FILES.ID = $self.ATTACHMENT_ID;
}

entity NC_RESPONSE_ATTACHMENTS {
  key ID             : UUID;
      NC_RESPONSE_ID : UUID;
      NC_RESPONSE    : Association to NCRESPONSES
                         on NC_RESPONSE.ID = $self.NC_RESPONSE_ID;
      ATTACHMENT_ID  : UUID;
      FILES          : Association to FILES
                         on FILES.ID = $self.ATTACHMENT_ID;
}

entity NOTIFICATIONS {
  key ID              : UUID;
      NAME            : String;
      TEXT            : String;
      ENTITY          : String;
      ENTITY_ID       : UUID;
      PERSONNEL_ID    : UUID;
      PERSONNEL       : Association to PERSONNELS
                         on PERSONNEL.ID = $self.PERSONNEL_ID;
      IS_READ         : Boolean;
      CREATED_AT      : Timestamp;
}