from . import api, view

views = [
    view.LobbyBlockCutProofHandler, view.LobbyColumnCutProofHandler, view.LobbyCharCutProofHandler,
    view.LobbyBlockCutReviewHandler, view.LobbyColumnCutReviewHandler, view.LobbyCharCutReviewHandler,
    view.CutProofDetailHandler, view.CutReviewDetailHandler,
    view.CharProofDetailHandler, view.CharReviewDetailHandler,
    view.TaskCutStatusHandler, view.TaskTextStatusHandler,
    view.TextProofTaskLobbyHandler, view.TextReviewTaskLobbyHandler, view.TextHardTaskLobbyHandler,
    view.TaskAdminHandler, view.MyTaskHandler,
]
handlers = [
    api.GetPageApi, api.GetPagesApi, api.UnlockTasksApi,
    api.PickCutProofTaskApi, api.PickCutReviewTaskApi, api.PickTextProofTaskApi, api.PickTextReviewTaskApi,
    api.SaveCutProofApi, api.SaveCutReviewApi,
    api.PublishTasksApi,
]
