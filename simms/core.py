#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Sphesihle Makhathini <sphemakh@gmail.com>
"""Uses the CASA simulate tool to create
an empty measurement set. Requires either an antenna table (CASA table)
or a list of ITRF or ENU positions.

A standard file should have the format:
    pos1 pos2 pos3* dish_diameter station mount.

NOTE: In the case of ENU, the 3rd position (up) is not essential
and may not be specified; indicate that your file doesn't have this
dimension by enebaling the --noup (-nu) option
"""

import argparse
import json
import logging
import os

import pkg_resources

from simms import casasm

__version__ = pkg_resources.get_distribution("simms").version


# I want to replace error() in argparse.ArgumentParser class
# I do this so I can catch the exception raised when too few arguments
# are parsed.
class ParserError(Exception):
    pass


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ParserError(message or "Not enough Arguments")


# Communication functions
def info(string):
    logging.info(string)


def warn(string):
    logging.warn(string)


def abort(string):
    logging.abort(string)


_ANTENNAS = {
    "meerkat": "meerkat.itrf.txt",
    "kat-7": "kat-7.itrf.txt",
    "jvla": "vlad.itrf.txt",
    "vla": "vlad.itrf.txt",
    "jvla-a": "vlaa.itrf.txt",
    "jvla-b": "vlab.itrf.txt",
    "jvla-c": "vlac.itrf.txt",
    "jvla-d": "vlad.itrf.txt",
    "vla-a": "vlaa.itrf.txt",
    "vla-b": "vlab.itrf.txt",
    "vla-c": "vlac.itrf.txt",
    "vla-d": "vlad.itrf.txt",
    "wsrt": "wsrt.itrf.txt",
    "ska1mid254": "skamid254.itrf.txt",
    "ska1mid197": "skamid197.itrf.txt",
    "lofar_nl": "lofar_nl.itrf.txt",
}

_OBS = {
    "meerkat": "meerkat",
    "kat-7": "kat-7",
    "wsrt": "wsrt",
    "ska1mid254": "meerkat",
    "ska1mid197": "meerkat",
    "lofar_nl": "lofar",
}

# possible combinations for specifying VLA configurations
VLA_CONFS = (
    ["vla"]
    + ["vla-%s" % s for s in "abcd"]
    + ["vla%s" % s for s in "abcd"]
    + ["vla_%s" % s for s in "abcd"]
    + ["jvla_%s" % s for s in "abcd"]
    + ["jvla-%s" % s for s in "abcd"]
    + ["jvla%s" % s for s in "abcd"]
)


def which_vla(name):
    name = name.lower()
    if name in ["vla", "jvla"]:
        return "jvla-d"
    elif name in VLA_CONFS:
        return "jvla-%s" % (name[-1])
    else:
        raise NameError("Telescope name could not recognised")


def create_empty_ms(
    msname=None,
    label=None,
    tel=None,
    pos=None,
    pos_type="casa",
    ra="0h0m0s",
    dec="-30d0m0s",
    synthesis=4,
    scan_length=[0],
    dtime=10,
    freq0=700e6,
    dfreq=50e6,
    nchan=1,
    stokes="XX XY YX YY",
    setlimits=False,
    elevation_limit=0,
    shadow_limit=0,
    outdir=None,
    nolog=False,
    coords="itrf",
    lon_lat=None,
    noup=False,
    nbands=1,
    direction=[],
    date=None,
    fromknown=False,
    feed="perfect X Y",
    scan_lag=0,
    auto_corr=False,
    optimise_start=None,
):
    """
    Uses the CASA simulate tool to create an empty measurement set. Requires
    either an antenna table (CASA table) or a list of ITRF or ENU positions.

    msname: MS name
    tel: Telescope name (This name must be in the CASA Database (check in me.obslist() in casa)
        If its not there, then you will need to specify the telescope coordinates via "lon_lat"
    pos: Antenna positions. This can either a CASA table or an ASCII file.
        (see simms --help for more on using an ascii file)
    pos_type: Antenna position type. Choices are (casa, ascii)
    coords: This is only applicable if you are using an ASCII file. Choices are (itrf, enu)
    synthesis: Synthesis time in hours
    dtime: Integration time in seconds
    freq0: Start frequency
    dfreq: Channel width
    nbands: Number of frequency bands
    **kw: extra keyword arguments.

    A standard file should have the format: pos1 pos2 pos3* dish_diameter station
    mount. NOTE: In the case of ENU, the 3rd position (up) is not essential and
    may not be specified; indicate that your file doesn't have this dimension by
    enebaling the --noup (-nu) option.
    """

    def toList_freq(item, nounits=False):
        items = item.split(",")
        if nounits:
            return list(map(int, items))
        else:
            try:
                items = list(map(float, items))
                return ["{:.4g}MHz".format(val / 1e6) for val in items]
            except ValueError:
                return items

    freq0 = toList_freq(freq0)
    dfreq = toList_freq(dfreq)
    nchan = toList_freq(nchan, nounits=True)

    if direction in [None, [], ()]:
        direction = ",".join(["J2000", ra, dec])
    if isinstance(direction, str):
        direction = [direction]

    if msname is None:
        msname = "%s_%dh%ss.MS" % (label or tel, synthesis, dtime)
    if outdir not in [None, "."]:
        msname = "%s/%s" % (outdir, msname)
        outdir = None

    if os.path.exists(msname):
        os.system("rm -fr %s" % msname)

    casasm.makems(
        msname=msname,
        label=label,
        tel=tel,
        pos=pos,
        pos_type=pos_type,
        synthesis=synthesis,
        scan_length=scan_length,
        dtime=dtime,
        freq0=freq0,
        dfreq=dfreq,
        nchan=nchan,
        stokes=stokes,
        setlimits=setlimits,
        elevation_limit=elevation_limit,
        shadow_limit=shadow_limit,
        coords=coords,
        lon_lat=lon_lat,
        noup=noup,
        nbands=nbands,
        direction=direction,
        outdir=outdir,
        date=date,
        fromknown=fromknown,
        feed=feed,
        scan_lag=scan_lag,
        auto_corr=auto_corr,
        optimise_start=optimise_start,
    )


def main():
    parser = ArgumentParser(
        description=__doc__,
    )
    add = parser.add_argument
    add(
        "-v",
        "--version",
        action="version",
        version="%s version %s" % (parser.prog, __version__),
    )
    add(
        "-ukc",
        "--use-known-config",
        dest="knownconfig",
        action="store_true",
        help="Use known antenna configuration. For some reason sm.setknownconfig() "
        "is not working. So this option does not work as yet.",
    )
    add("pos", help="Antenna positions", nargs="?")
    add(
        "-t",
        "--type",
        dest="type",
        default="casa",
        choices=["casa", "ascii"],
        help="position list type : dafault is casa",
    )
    add(
        "-cs",
        "--coord-sys",
        dest="coords",
        default="itrf",
        choices=["itrf", "enu", "wgs84"],
        help="Only relevent when --type=ascii. Coordinate system of antenna positions."
        " :dafault is itrf",
    )
    add(
        "-lle",
        "--lon-lat-elv",
        dest="lon_lat",
        help="Reference position of telescope. Comma "
        "seperated longitude,lattitude and elevation [deg,deg,m]. "
        "Elevation is not crucial, lon,lat should be enough. If not specified,"
        " we'll try to get this info from the CASA database "
        "(assuming that your observatory is known to CASA; --tel, -T): No default",
    )
    add(
        "-nu",
        "--noup",
        dest="noup",
        action="store_true",
        help="Enable this to indicate that your ENU file does not have an "
        "'up' dimension: This is not the default",
    )
    add("-T", "--tel", dest="tel", help="Telescope name : no default")
    add(
        "-n",
        "--name",
        dest="name",
        help="MS name. A name based on the observatoion will be generated otherwise.",
    )
    add(
        "-od",
        "--outdir",
        dest="outdir",
        default=".",
        help="Directory in which to save the MS: default is working directory",
    )
    add(
        "-l",
        "--label",
        dest="label",
        help="Label to add to the auto generated MS name (if --name is not given)",
    )
    add(
        "-dir",
        "--direction",
        dest="direction",
        action="append",
        default=[],
        help="Pointing direction. Example J2000,0h0m0s,-30d0m0d. Option "
        "--direction may be specified multiple times for multiple pointings",
    )
    add(
        "-ra",
        "--ra",
        dest="ra",
        default="0h0m0s",
        help="Right Assention in hms or val[unit] : default is 0h0m0s",
    )
    add(
        "-dec",
        "--dec",
        dest="dec",
        default="-30d0m0s",
        type=str,
        help="Declination in dms or val[unit]: default is -30d0m0s",
    )
    add(
        "-st",
        "--synthesis-time",
        dest="synthesis",
        default=4,
        type=float,
        help="Synthesis time in hours: default is 4.0",
    )
    add(
        "-sl",
        "--scan-length",
        action="append",
        dest="scan_length",
        type=str,
        help="Synthesis time in hours: default is the sysntheis time",
    )
    add(
        "-dt",
        "--dtime",
        dest="dtime",
        default=10,
        type=float,
        help="Integration time in seconds : default is 10s",
    )
    add(
        "-ih",
        "--init-ha",
        dest="init_ha",
        default=None,
        help="Initial hour angle for observation. If not specified "
        "we use -[scan_length/2]:: DEPRECATED",
    )
    add(
        "-nc",
        "--nchan",
        dest="nchan",
        default="1",
        help="Number of frequency channels. Specify as comma separated list "
        " (for multiple subbands); see also --freq0, --dfreq: default is 1",
    )
    add(
        "-f0",
        "--freq0",
        dest="freq0",
        default="700MHz",
        help="Start frequency. Specify as val[unit]. E.g 700MHz, not unit => Hz ."
        " Use a comma seperated list for multiple start frequencies "
        "(for multiple subbands); see also --nchan, --dfreq: default is 700MHz",
    )
    add(
        "-df",
        "--dfreq",
        dest="dfreq",
        default="50MHz",
        help="Channel width. Specify as val[unit]. E.g 700MHz, not unit => Hz "
        "Use a comma separated list of channel widths (for multiple subbands);"
        " see also --nchan, --freq0 : default is 50MHz",
    )
    add(
        "-nb",
        "--nband",
        dest="nband",
        default=1,
        type=int,
        help="Number of subbands : default is 1",
    )
    add(
        "-pl",
        "--pol",
        dest="pol",
        nargs="+",
        default="XX XY YX YY".split(),
        help="Polarization : default is XX XY YX YY",
    )
    add(
        "-feed",
        "--feed",
        dest="feed",
        nargs="+",
        default="perfect X Y".split(),
        help='Polarization : default is "perfect X Y" ',
    )
    add(
        "-date",
        "--date",
        dest="date",
        metavar="EPOCH,yyyy/mm/dd[/h:m:s]",
        help='Date of observation. Example "UTC,2014/05/26" or "UTC,2014/05/26/12:12:12" : default is today',
    )
    add(
        "-os",
        "--optimise-start",
        action="store_true",
        help="Modify observation start time to maximise source visibility.",
    )
    add(
        "-slg",
        "--scan-lag",
        default=0,
        type=float,
        help="Lag time between scans. In hrs: default is 0:: DEPRECATED",
    )
    add(
        "-stl",
        "--set-limits",
        dest="set_limits",
        action="store_true",
        help="Set telescope limits; elevation and shadow limts : not the default",
    )
    add(
        "-el",
        "--elevation-limit",
        dest="elevation_limit",
        type=float,
        default=0,
        help="Dish elevation limit. Will only be taken into account if --set-limits (-stl) is enabled : no default",
    )
    add(
        "-shl",
        "--shadow-limit",
        dest="shadow_limit",
        type=float,
        default=0,
        help="Shadow limit. Will only be taken into account if --set-limits (-stl) is enabled : no default",
    )
    add(
        "-ac",
        "--auto-correlations",
        dest="auto_corr",
        action="store_true",
        help="Don't keep Log file : not the default",
    )
    add(
        "-ng",
        "--nolog",
        dest="nolog",
        action="store_true",
        help="Don't keep Log file : not the default",
    )
    add("-jc", "--json-config", dest="config", help="Json config file : No default")

    args = parser.parse_args()

    if args.config:
        with open(args.config) as conf:
            jdict = json.load(conf)

        for key, val in jdict.items():
            if isinstance(val, str):
                jdict[key] = str(val)

        tel = jdict["tel"]
        if tel in list(_ANTENNAS.keys()) + VLA_CONFS and not jdict.get("pos", False):
            if tel[:-3] in ["vla", "jvl"]:
                pos = which_vla(tel)
                jdict["tel"] = "vla"
            else:
                pos = jdict["tel"]
            # jdict["pos"] = "%s/observatories/%s" % (simms_path, _ANTENNAS[pos])
            jdict["pos"] = pkg_resources.resource_filename(
                "simms.observatories", _ANTENNAS[pos]
            )
            jdict["pos_type"] = "ascii"
            jdict["coords"] = "itrf"

    else:
        if (not args.tel) and (not args.lon_lat):
            raise parser.error(
                "Either the telescope name (--tel/-T) or Telescope coordinate (-lle/--lon-lat )is required"
            )

        telescope = args.tel.lower()
        if telescope in list(_ANTENNAS.keys()) + VLA_CONFS and args.pos == None:
            if telescope[:3] in ["vla", "jvl"] and args.pos in [None, False, ""]:
                pos = which_vla(telescope)
                telescope = "vla"
            else:
                pos = _OBS[args.tel.lower()]
                telescope = _OBS[pos]
            antennas = pkg_resources.resource_filename(
                "simms.observatories", _ANTENNAS[pos]
            )

            _type = "ascii"
            cs = "itrf"
        else:
            antennas = args.pos
            telescope = args.tel
            _type = args.type
            cs = args.coords
        jdict = dict(
            msname=args.name,
            label=args.label,
            tel=telescope,
            pos=antennas,
            feed=" ".join(args.feed),
            pos_type=_type,
            ra=args.ra,
            dec=args.dec,
            synthesis=args.synthesis,
            scan_length=args.scan_length,
            dtime=args.dtime,
            freq0=args.freq0,
            dfreq=args.dfreq,
            nchan=args.nchan,
            stokes=" ".join(args.pol),
            setlimits=args.set_limits,
            elevation_limit=args.elevation_limit,
            shadow_limit=args.shadow_limit,
            outdir=args.outdir,
            coords=cs,
            lon_lat=args.lon_lat,
            noup=args.noup,
            direction=args.direction,
            nbands=args.nband,
            date=args.date,
            optimise_start=args.optimise_start,
            scan_lag=args.scan_lag,
            auto_corr=args.auto_corr,
            nolog=args.nolog,
        )

        create_empty_ms(**jdict)


if __name__ == "__main__":
    main()
