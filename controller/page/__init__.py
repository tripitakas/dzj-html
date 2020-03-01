from . import view, api, ocr, data

views = [
    data.PageAdminHandler, data.PageBrowseHandler, data.PageInfoHandler,
    view.TaskCutHandler, view.CutEditHandler,
    view.TaskTextProofHandler, view.TaskTextReviewHandler, view.TextEditHandler,
]

handlers = [
    data.PageUpdateSourceApi, data.PageExportCharApi, data.PageUploadApi,
    ocr.FetchTasksApi, ocr.SubmitTasksApi, ocr.ConfirmFetchTasksApi,
    api.TaskCutApi, api.CutEditApi,
    api.TaskTextSelectApi, api.TaskTextProofApi, api.TaskTextReviewApi, api.TaskTextHardApi,
    api.TextEditApi, api.TextNeighborApi, api.TextsDiffApi, api.DetectWideCharsApi,
]

modules = {'TextArea': view.TextArea}
