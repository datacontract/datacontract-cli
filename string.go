package main

func EqualStringPointers(s1, s2 *string) bool {
	// both are the same (e.g. nil)
	if s1 == s2 {
		return true
	}

	// one pointer is nil, the other not
	if (s1 == nil && s2 != nil) || (s1 != nil && s2 == nil) {
		return false
	}

	return *s1 == *s2
}

func StringPointerString(str *string) string {
	if str == nil {
		return ""
	}

	return *str
}
