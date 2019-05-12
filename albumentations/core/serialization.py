import json
import warnings

try:
    import yaml
    yaml_available = True
except ImportError:
    yaml_available = False


from albumentations import __version__


__all__ = ['to_dict', 'from_dict', 'save', 'load']


SERIALIZABLE_REGISTRY = {}


class SerializableMeta(type):
    """
    A metaclass that is used to register classes in `SERIALIZABLE_REGISTRY` so they can be found later
    while deserializing transformation pipeline using classes full names.
    """

    def __new__(meta, name, bases, class_dict):
        cls = type.__new__(meta, name, bases, class_dict)
        SERIALIZABLE_REGISTRY[cls.get_class_fullname()] = cls
        return cls


def to_dict(transform, on_not_implemented_error='raise'):
    """
    Takes a transforms pipeline and converts it to a serializable representation that uses only standard
    python data types: dictionaries, lists, strings, integers, and floats.

    Args:
        transform (object): A transform that should be serialized. If the transform doesn't implement the `to_dict`
            method and `on_not_implemented_error` equals to 'raise' then `NotImplementedError` is raised.
            If `on_not_implemented_error` equals to 'warn' then `NotImplementedError` will be ignored
            but no transform parameters will be serialized.
    """

    if on_not_implemented_error not in {'raise', 'warn'}:
        raise ValueError(
            "Unknown on_not_implemented_error value: {}. Supported values are: 'raise' and 'warn'".format(
                on_not_implemented_error
            )
        )
    try:
        transform_dict = transform.to_dict()
    except NotImplementedError as e:
        if on_not_implemented_error == 'raise':
            raise e
        else:
            transform_dict = {}
            warnings.warn(
                "Got NotImplementedError while trying to serialize {obj}. Object arguments are not preserved. "
                "Implement either '{cls_name}.get_transform_init_args_names' or '{cls_name}.get_transform_init_args' "
                "method to make the transform serializable".format(
                    obj=transform,
                    cls_name=transform.__class__.__name__,
                )
            )
    return {
        '__version__': __version__,
        'transform': transform_dict,
    }


def from_dict(transform_dict):
    """
    Args:
        transform (dict): A dictionary with serialized transform pipeline.
    """

    transform = transform_dict['transform']
    name = transform['__class_fullname__']
    args = {k: v for k, v in transform.items() if k != '__class_fullname__'}
    cls = SERIALIZABLE_REGISTRY[name]
    if 'transforms' in args:
        args['transforms'] = [from_dict({'transform': t}) for t in args['transforms']]
    return cls(**args)


def check_data_format(data_format):
    if data_format not in {'json', 'yaml'}:
        raise ValueError(
            "Unknown data_format {}. Supported formats are: 'json' and 'yaml'".format(data_format)
        )


def save(transform, filepath, data_format='json', on_not_implemented_error='raise'):
    """
    Takes a transform pipeline, serializes it and saves a serialized version to a file
    using either json or yaml format.

    Args:
        transform (obj): Transform to serialize.
        filepath (str): Filepath to write to.
        data_format (str): Serialization format. Should be either `json` or 'yaml'.
        on_not_implemented_error (str): Parameter that describes what to do if a transform doesn't implement
            the `to_dict` method. If 'raise' then `NotImplementedError` is raised, if `warn` then the exception will be
            ignored and no transform arguments will be saved.
    """

    check_data_format(data_format)
    transform_dict = to_dict(transform, on_not_implemented_error=on_not_implemented_error)
    dump_fn = json.dump if data_format == 'json' else yaml.dump
    with open(filepath, 'w') as f:
        dump_fn(transform_dict, f)


def load(filepath, data_format='json'):
    """
    Loads a serialized pipeline from a json or yaml file and constructs a transform pipeline.

    Args:
        transform (obj): Transform to serialize.
        filepath (str): Filepath to read from.
        data_format (str): Serialization format. Should be either `json` or 'yaml'.
    """

    check_data_format(data_format)
    load_fn = json.load if data_format == 'json' else yaml.load
    with open(filepath) as f:
        transform_dict = load_fn(f)
    return from_dict(transform_dict)
