from . import api_base, api_publish, api_text, api_cut, view_admin, view_cut, view_lobby, view_my, view_text

views = [
    view_lobby.TaskLobbyHandler, view_my.MyTaskHandler,
    view_admin.TaskAdminHandler, view_admin.TaskInfoHandler,
    view_text.TextProofHandler, view_text.TextReviewHandler, view_text.TextHardHandler,
    view_cut.CutHandler, view_cut.OCRHandler,
]
handlers = [
    api_base.PickTaskApi, api_base.ReturnTaskApi, api_base.GetPageApi,
    api_base.UnlockTaskDataApi, api_base.WithDrawTaskApi, api_base.ResetTaskApi,
    api_publish.GetReadyTasksApi, api_publish.PublishTasksPageNamesApi, api_publish.PublishTasksPagePrefixApi,
    api_text.SaveTextProofApi, api_text.SaveTextReviewApi, api_text.SaveTextHardApi,
    api_text.GetCompareTextApi, api_text.GetCompareNeighborApi,
    api_cut.SaveCutApi, api_cut.SaveCutEditApi, api_cut.SaveOCRApi,
]
modules = {'TextArea': view_text.TextArea}
