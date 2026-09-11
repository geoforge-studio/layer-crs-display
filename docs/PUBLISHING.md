# Publication checklist

## Repository preparation complete

- GeoForge Studio maintainer identity and neutral internal identifiers.
- Separate runtime source, documentation and development tests.
- GPL-2.0-or-later licensing and complete license text.
- Deterministic installable ZIP builder with a publication metadata gate.
- Public contact: reynolds.mach88@gmail.com.
- Public source: https://github.com/geoforge-studio/layer-crs-display
- Issue tracker: https://github.com/geoforge-studio/layer-crs-display/issues
- Experimental flag while native acceptance remains pending.

## Before QGIS submission

1. Complete native testing in `TESTING.md`; record actual tested versions/platforms.
2. Confirm that homepage, repository and issue-tracker URLs remain accessible.
3. Run `python tools/build_zip.py --release`. Keep experimental status unless
   native validation supports a stable release. The ZIP must match the committed
   source. GitHub's auto-generated source ZIP is not the QGIS installation archive.
4. Upload the installation ZIP to the QGIS plugin portal. Automated security
   checks and manual review still apply; publishing source on GitHub does not
   mean the plugin has been approved by QGIS.

## OSGeo request, if needed

Use the following code repository for **Source Code URL**:

https://github.com/geoforge-studio/layer-crs-display

For **Affiliation Link**, the GeoForge profile can be used if it establishes the
requested association with the public contact email. The repository README also
identifies the maintainer and the public contact address. The QGIS portal offers
GitHub/GitLab/Google sign-in as well; OSGeo registration is not the only login route.

## Privacy when publishing

Use the selected public brand name and the intended commit email. Do not publish
private datasets or unredacted batch reports. Reports contain paths, layer names
and subset filters. Changing a profile does not rewrite old Git author details.

## Official references

- https://plugins.qgis.org/docs/publish
- https://plugins.qgis.org/docs/approval
- https://plugins.qgis.org/accounts/login/
- https://id.osgeo.org/ldap/create
