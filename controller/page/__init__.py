from . import view, api, ocr

views = [
    view.PageBrowseHandler, view.PageViewHandler,
    view.TaskCutHandler, view.CutEditHandler,
    view.TaskTextProofHandler, view.TaskTextReviewHandler, view.TextEditHandler,
    view.CharEditHandler, view.BoxHandler, view.OrderHandler,
    view.PageListHandler, view.PageInfoHandler, view.CharListHandler,
    view.CharStatisticHandler,
]

handlers = [
    ocr.FetchTasksApi, ocr.SubmitTasksApi, ocr.ConfirmFetchTasksApi,
    api.TaskPublishApi, api.TaskCutApi, api.CutEditApi,
    api.TaskTextSelectApi, api.TaskTextProofApi, api.TaskTextReviewApi, api.TaskTextHardApi,
    api.TextEditApi, api.TextNeighborApi, api.TextsDiffApi, api.DetectWideCharsApi,
    api.UpdatePageSourceApi, api.PageExportCharsApi,
    api.PageBoxApi,
]

modules = {'TextArea': view.TextArea}
