from . import view, api, task, ocr

views = [
    view.PageListHandler, view.PageBrowseHandler, view.PageViewHandler, view.PageInfoHandler,
    view.PageBoxHandler, view.PageOrderHandler, view.PageCmpTxtHandler,
    view.PageTxtHandler, view.PageTextHandler,
]

handlers = [
    ocr.FetchTasksApi, ocr.SubmitTasksApi, ocr.ConfirmFetchApi,
    api.TaskPublishApi, api.TaskCutApi, api.CutEditApi,
    api.SelectCmpTxtApi, api.TaskTextProofApi, api.TaskTextReviewApi, api.TaskTextHardApi,
    api.TextEditApi, api.TextNeighborApi, api.TextsDiffApi, api.DetectWideCharsApi,
    api.UpdatePageSourceApi, api.PageExportCharsApi,
    api.PageBoxApi,

]

modules = {'TextArea': view.TextArea}
