try:
    from .reorder_ import char_reorder
except ImportError:
    def char_reorder(chars, blocks=None, sort=True, remove_outside=True, img_file=''):
        pass
