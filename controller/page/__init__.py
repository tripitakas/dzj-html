from . import view, api, ocr

views = [
    view.PageBrowseHandler,
    view.TaskCutHandler, view.CutEditHandler,
    view.TaskTextProofHandler, view.TaskTextReviewHandler, view.TextEditHandler,
]

handlers = [
    ocr.FetchTasksApi, ocr.SubmitTasksApi, ocr.ConfirmFetchTasksApi,
    api.TaskCutApi, api.CutEditApi,
    api.TaskTextSelectApi, api.TaskTextProofApi, api.TaskTextReviewApi, api.TaskTextHardApi,
    api.TextEditApi, api.TextNeighborApi, api.TextsDiffApi, api.DetectWideCharsApi,
]

modules = {'TextArea': view.TextArea}
