from . import api, api_publish, api_text, api_cut, view, view_cut, view_text

views = [
    view.TaskLobbyHandler, view.MyTaskHandler,
    view.TaskAdminHandler, view.TaskInfoHandler,
    view_text.TextProofHandler, view_text.TextReviewHandler, view_text.TextHardHandler,
    view_cut.CutHandler, view_cut.OCRHandler,
]
handlers = [
    api.PickTaskApi, api.ReturnTaskApi, api.GetPageApi,
    api.UnlockTaskDataApi, api.RetrieveTaskApi, api.DeleteTasksApi,
    api_publish.GetReadyTasksApi, api_publish.PublishTasksByFileApi, api_publish.PublishTasksByPrefixApi,
    api_publish.PublishTasksByIdsApi,
    api_text.SaveTextProofApi, api_text.SaveTextReviewApi, api_text.SaveTextHardApi,
    api_text.GetCompareTextApi, api_text.GetCompareNeighborApi,
    api_cut.SaveCutApi, api_cut.SaveCutEditApi, api_cut.SaveOCRApi,
]
modules = {'TextArea': view_text.TextArea}
