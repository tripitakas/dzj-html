from . import view, api, ocr

views = [
    view.PageAdminHandler, view.PageBrowseHandler, view.PageViewHandler, view.PageInfoHandler,
    view.PageBoxHandler, view.PageOrderHandler, view.PageCmpTxtHandler,
    view.PageTxtHandler, view.PageTextHandler,
    view.PageTaskAdminHandler, view.PageTaskStatHandler, view.PageTaskResumeHandler,
    view.PageTaskLobbyHandler, view.PageTaskMyHandler,
]

handlers = [
    ocr.FetchTasksApi, ocr.SubmitTasksApi, ocr.ConfirmFetchApi,
    api.PageDeleteApi,
    api.PageBoxApi, api.PageOrderApi, api.PageCmpTxtApi, api.PageCmpTxtNeighborApi,
    api.PageTxtDiffApi, api.PageDetectCharsApi, api.PageExportCharsApi, api.PageSourceApi,
    api.PageTaskPublishApi, api.PageUpsertApi,
]

modules = {'TextArea': view.TextArea}
