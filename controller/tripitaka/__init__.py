from . import view, api, tripitaka, volume, sutra, reel

views = [
    view.RsTripitakaHandler, view.TripitakaListHandler, view.TripitakaHandler,
]

handlers = [
    tripitaka.TripitakaAddOrUpdateApi, tripitaka.TripitakaUploadApi, tripitaka.TripitakaDeleteApi,
    volume.VolumeAddOrUpdateApi, volume.VolumeUploadApi, volume.VolumeDeleteApi,
    sutra.SutraAddOrUpdateApi, sutra.SutraUploadApi, sutra.SutraDeleteApi,
    reel.ReelAddOrUpdateApi, reel.ReelUploadApi, reel.ReelDeleteApi,
]
