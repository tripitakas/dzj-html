from . import view, api, ocr

views = [
    view.PageListHandler, view.PageBrowseHandler, view.PageViewHandler, view.PageInfoHandler,
    view.PageBoxHandler, view.PageOrderHandler, view.PageCmpTxtHandler,
    view.PageTxtHandler, view.PageTextHandler,
    view.PageTaskAdminHandler, view.PageTaskStatHandler, view.PageTaskResumeHandler,
    view.PageCutTaskHandler, view.PageTxtTaskHandler,
]

handlers = [
    ocr.FetchTasksApi, ocr.SubmitTasksApi, ocr.ConfirmFetchApi,
    api.PageDeleteApi, api.PageUpsertApi,
    api.PageBoxApi, api.PageOrderApi, api.PageCmpTxtApi, api.PageCmpTxtNeighborApi,
    api.PageTxtDiffApi, api.PageDetectCharsApi, api.PageExportCharsApi, api.PageSourceApi,
    api.PageTaskPublishApi, api.PageCutTaskApi,
]

modules = {'TextArea': view.TextArea}
