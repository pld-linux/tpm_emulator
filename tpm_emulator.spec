#
# Conditional build:
%bcond_without	dist_kernel	# without distribution kernel
%bcond_without  kernel		# don't build kernel modules
%bcond_without	userspace	# don't build userspace packages
%bcond_with	verbose		# verbose kernel module build
#
%if %{without kernel}
%undefine	with_dist_kernel
%endif

# The goal here is to have main, userspace, package built once with
# simple release number, and only rebuild kernel packages with kernel
# version as part of release number, without the need to bump release
# with every kernel change.
%if 0%{?_pld_builder:1} && %{with kernel} && %{with userspace}
%{error:kernel and userspace cannot be built at the same time on PLD builders}
exit 1
%endif

%if "%{_alt_kernel}" != "%{nil}"
%if 0%{?build_kernels:1}
%{error:alt_kernel and build_kernels are mutually exclusive}
exit 1
%endif
%undefine	with_userspace
%global		_build_kernels		%{alt_kernel}
%else
%global		_build_kernels		%{?build_kernels:,%{?build_kernels}}
%endif

%if %{without userspace}
# nothing to be placed to debuginfo package
%define		_enable_debug_packages	0
%endif

%define		_duplicate_files_terminate_build	0

%define		kpkg	%(echo %{_build_kernels} | tr , '\\n' | while read n ; do echo %%undefine alt_kernel ; [ -z "$n" ] || echo %%define alt_kernel $n ; echo %%kernel_pkg ; done)
%define		bkpkg	%(echo %{_build_kernels} | tr , '\\n' | while read n ; do echo %%undefine alt_kernel ; [ -z "$n" ] || echo %%define alt_kernel $n ; echo %%build_kernel_pkg ; done)

%define	pname	tpm_emulator
%define	rel	9
Summary:	Software-based TPM and MTM Emulator
Summary(pl.UTF-8):	Programowy emulator TPM i MTM
Name:		%{pname}%{_alt_kernel}
Version:	0.7.4
Release:	%{rel}%{?with_kernel:@%{_kernel_ver_str}}
License:	GPL v2+
Group:		Applications/System
Source0:	http://downloads.sourceforge.net/tpm-emulator.berlios/%{pname}-%{version}.tar.gz
# Source0-md5:	e26becb8a6a2b6695f6b3e8097593db8
Patch0:		%{pname}-libdir.patch
URL:		http://tpm-emulator.berlios.de/
BuildRequires:	cmake >= 2.4
BuildRequires:	gmp-devel
BuildRequires:	rpmbuild(macros) >= 1.678
%{?with_dist_kernel:BuildRequires:	kernel%{_alt_kernel}-module-build >= 3:2.6.20.2}
Requires:	%{name}-libs = %{version}-%{rel}
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
Software-based TPM and MTM Emulator.

%description -l pl.UTF-8
Programowy emulator TPM i MTM.

%package libs
Summary:	TSS-conformant device driver library for the emulator
Summary(pl.UTF-8):	Biblioteka sterownika urządzenia zgodnego z TSS dla emulatora
Group:		Libraries

%description libs
TSS-conformant device driver library for the emulator.

%description libs -l pl.UTF-8
Biblioteka sterownika urządzenia zgodnego z TSS dla emulatora.

%package devel
Summary:	Header file for TDDL library
Summary(pl.UTF-8):	Plik nagłówkowy biblioteki TDDL
Group:		Development/Libraries
Requires:	%{name}-libs = %{version}-%{rel}

%description devel
Header file for TDDL library.

%description devel -l pl.UTF-8
Plik nagłówkowy biblioteki TDDL.

%package static
Summary:	Static TDDL library
Summary(pl.UTF-8):	Statyczna biblioteka TDDL
Group:		Development/Libraries
Requires:	%{name}-devel = %{version}-%{rel}

%description static
Static TDDL library.

%description static -l pl.UTF-8
Statyczna biblioteka TDDL.

%define	kernel_pkg()\
%package -n kernel%{_alt_kernel}-char-tpmd\
Summary:	Kernel module that provides /dev/tpm device\
Summary(pl.UTF-8):	Moduł jądra udostępniający urządzenie /dev/tpm\
Release:	%{rel}@%{_kernel_ver_str}\
Group:		Base/Kernel\
%if %{with dist_kernel}\
%requires_releq_kernel\
Requires(postun):	%releq_kernel\
%endif\
\
%description -n kernel%{_alt_kernel}-char-tpmd\
Kernel module that provides /dev/tpm device for backward compatibility\
and forwards the received commands to tpmd.\
\
%description -n kernel%{_alt_kernel}-char-tpmd -l pl.UTF-8\
Moduł jądra udostępniający dla kompatybilności urządzenie /dev/tpm i\
przekazujący odebrane polecenia do tpmd.\
\
%if %{with kernel}\
%files -n kernel%{_alt_kernel}-char-tpmd\
%defattr(644,root,root,755)\
/lib/modules/%{_kernel_ver}/misc/tpmd_dev.ko*\
/lib/udev/rules.d/80-tpmd_dev.rules\
%endif\
\
%post	-n kernel%{_alt_kernel}-char-tpmd\
%depmod %{_kernel_ver}\
\
%postun	-n kernel%{_alt_kernel}-char-tpmd\
%depmod %{_kernel_ver}\
%{nil}

%define build_kernel_pkg()\
%build_kernel_modules -m tpmd_dev -C tpmd_dev/linux\
%install_kernel_modules -D installed -m tpmd_dev/linux/tpmd_dev -d misc\
%{nil}

%{?with_kernel:%{expand:%kpkg}}

%prep
%setup -q -n %{pname}-%{version}
%patch0 -p1

# separate kernel module from userspace build
echo > tpmd_dev/CMakeLists.txt

%build
mkdir build
cd build
%cmake ..
%if %{with userspace}
%{__make}
%endif
cd ..
%if %{with kernel}
ln -sf ../../build/config.h tpmd_dev/linux/config.h
%{__make} -C tpmd_dev/linux tpmd_dev.rules
%{expand:%bkpkg}
%endif

%install
rm -rf $RPM_BUILD_ROOT

%if %{with userspace}
%{__make} -C build install \
	DESTDIR=$RPM_BUILD_ROOT
%endif

%if %{with kernel}
install -d $RPM_BUILD_ROOT/lib/udev/rules.d
cp -p tpmd_dev/linux/tpmd_dev.rules $RPM_BUILD_ROOT/lib/udev/rules.d/80-tpmd_dev.rules
cp -a installed/* $RPM_BUILD_ROOT
%endif

%clean
rm -rf $RPM_BUILD_ROOT

%post	libs -p /sbin/ldconfig
%postun	libs -p /sbin/ldconfig

%if %{with userspace}
%files
%defattr(644,root,root,755)
%doc AUTHORS ChangeLog README
%attr(755,root,root) %{_bindir}/tpmd

%files libs
%defattr(644,root,root,755)
%attr(755,root,root) %{_libdir}/libtddl.so.*.*.*.*
%attr(755,root,root) %ghost %{_libdir}/libtddl.so.1.2

%files devel
%defattr(644,root,root,755)
%attr(755,root,root) %{_libdir}/libtddl.so
%{_includedir}/tddl.h

%files static
%defattr(644,root,root,755)
%{_libdir}/libtddl.a
%endif
