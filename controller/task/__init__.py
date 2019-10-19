from . import api, view

views = [
    view.TaskLobbyHandler, view.MyTaskHandler, view.TaskAdminHandler,
]

handlers = [
    api.GetReadyTasksApi, api.PublishTasksApi, api.AssignTasksApi, api.DeleteTasksApi,
    api.RetrieveTaskApi, api.PickTaskApi, api.ReturnTaskApi, api.FinishTaskApi,
    api.LockTaskDataApi, api.UnlockTaskDataApi,
]
