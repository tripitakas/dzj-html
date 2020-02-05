from . import api, view

views = [
    view.LobbyTaskHandler, view.MyTaskHandler, view.DocTaskAdminHandler, view.ImageTaskAdminHandler,
    view.PageTaskResumeHandler, view.DocTaskStatisticHandler,
    view.TaskDetailHandler, view.TaskSampleHandler,
]

handlers = [
    api.PublishDocTasksApi, api.PublishImageTasksApi, api.RepublishTaskApi,
    api.GetReadyDocsApi, api.AssignTasksApi, api.DeleteTasksApi, api.UpdateTaskApi,
    api.PickTaskApi, api.ReturnTaskApi, api.FinishTaskApi, api.LockTaskApi,
    api.UnlockTaskApi, api.InitTestTasksApi,
]
