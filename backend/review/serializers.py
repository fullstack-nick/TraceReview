import math
from collections.abc import Mapping
from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError({"form": ["Expected an object."]})
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({field: ["Unsupported field."] for field in sorted(unknown)})
        return super().to_internal_value(data)


class FiniteNumber(serializers.FloatField):
    def to_internal_value(self, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise serializers.ValidationError("Enter a finite JSON number.")
        result = super().to_internal_value(value)
        if not math.isfinite(result):
            raise serializers.ValidationError("Enter a finite number.")
        return result


class PreviewSerializer(StrictSerializer):
    start_time = FiniteNumber()
    end_time = FiniteNumber()


class RevisionSerializer(PreviewSerializer):
    reason = serializers.CharField(max_length=1000, allow_blank=False, trim_whitespace=True)
    expected_version = serializers.IntegerField(min_value=1)
    request_id = serializers.UUIDField()


class CompletionSerializer(StrictSerializer):
    revision_id = serializers.UUIDField()
    expected_version = serializers.IntegerField(min_value=1)
    request_id = serializers.UUIDField()
    review_note = serializers.CharField(max_length=2000, allow_blank=True, default="", trim_whitespace=True)


class ImportSerializer(StrictSerializer):
    file = serializers.FileField()
    label = serializers.CharField(max_length=120, allow_blank=False, required=False, trim_whitespace=True)
    request_id = serializers.UUIDField()
