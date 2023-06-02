"""

term := o.environ.Getenv("TERM")
if strings.HasPrefix(term, "screen") || strings.HasPrefix(term, "tmux") {
    return "", ErrStatusReport
}

---

pgrp, err := unix.IoctlGetInt(fd, unix.TIOCGPGRP)
if err != nil {
    return false
}

g, err := unix.Getpgrp()
if err != nil {
    return false
}

return pgrp == g


"""


"""

Color profile win:


func (o *Output) ColorProfile() Profile {
	if !o.isTTY() {
		return Ascii
	}

	if o.environ.Getenv("ConEmuANSI") == "ON" {
		return TrueColor
	}

	winVersion, _, buildNumber := windows.RtlGetNtVersionNumbers()
	if buildNumber < 10586 || winVersion < 10 {
		// No ANSI support before Windows 10 build 10586.
		if o.environ.Getenv("ANSICON") != "" {
			conVersion := o.environ.Getenv("ANSICON_VER")
			cv, err := strconv.ParseInt(conVersion, 10, 64)
			if err != nil || cv < 181 {
				// No 8 bit color support before v1.81 release.
				return ANSI
			}

			return ANSI256
		}

		return Ascii
	}
	if buildNumber < 14931 {
		// No true color support before build 14931.
		return ANSI256
	}

	return TrueColor
}



EnableVirtualTerminalProcessing??

"""
