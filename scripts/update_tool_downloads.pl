#!/usr/bin/env perl
use strict;
use warnings;

use File::Basename qw(dirname);
use File::Spec;
use HTTP::Tiny;
use JSON::PP qw(decode_json);
use List::Util qw(sum0);
use POSIX qw(strftime);

my $ROOT = File::Spec->rel2abs(File::Spec->catdir(dirname(__FILE__), File::Spec->updir));
my $PAGE = File::Spec->catfile($ROOT, 'software.html');

# Download values remain source-specific rather than being combined. GitHub stars
# are a separate popularity signal and are refreshed for every linked repository.
my %SOURCES = (
    lotus3      => [bioconda => 'bioconda/lotus3'],
    matafiler4  => [github   => 'hildebra/MATAFILER4'],
    protal      => [bioconda => 'bioconda/protal'],
    rtk         => [cran     => 'rtk'],
    clustermags => [github   => 'hildebra/clusterMAGs'],
    cvanmf      => [bioconda => 'bioconda/cvanmf'],
    adhesiomer  => [github   => 'ksidorczuk/adhesiomeR'],
    sdm         => [bioconda => 'bioconda/sdm'],
    lca         => [bioconda => 'bioconda/lca'],
    msafix      => [github   => 'hildebra/MSAfix'],
    bmtk        => [github   => 'apduncan/bm-tk'],
    vcf2fna     => [github   => 'hildebra/vcf2fna'],
    metamage    => [github   => '4less/meta-mage'],
    benchpro    => [github   => '4less/benchpro'],
    newvu       => [github   => '4less/newvu'],
    enterosig   => [github   => 'apduncan/enterosig_sl'],
    lotus2      => [bioconda => 'bioconda/lotus2'],
    matafiler   => [github   => 'hildebra/MATAFILER'],
    mgtk        => [github   => 'hildebra/mg-tk'],
);

my %REPOSITORIES = (
    lotus3      => 'hildebra/LotuS3',
    matafiler4  => 'hildebra/MATAFILER4',
    protal      => '4less/protal',
    rtk         => 'hildebra/Rarefaction',
    clustermags => 'hildebra/clusterMAGs',
    cvanmf      => 'apduncan/cvanmf',
    adhesiomer  => 'ksidorczuk/adhesiomeR',
    sdm         => 'hildebra/sdm',
    lca         => 'hildebra/LCA',
    msafix      => 'hildebra/MSAfix',
    canopy2     => 'hildebra/canopy2',
    bmtk        => 'apduncan/bm-tk',
    vcf2fna     => 'hildebra/vcf2fna',
    metamage    => '4less/meta-mage',
    benchpro    => '4less/benchpro',
    newvu       => '4less/newvu',
    enterosig   => 'apduncan/enterosig_sl',
    lotus2      => 'hildebra/lotus2',
    matafiler   => 'hildebra/MATAFILER',
    mgtk        => 'hildebra/mg-tk',
);

my $CRANLOGS_START = '2012-10-01';
my %TAGGED_VERSION_REPOSITORIES = (
    canopy2 => 'hildebra/canopy2',
);

my %DOWNLOAD_LABELS = (
    bioconda => 'Bioconda downloads',
    cran     => 'CRAN downloads',
    github   => 'GitHub release downloads',
);

my $HTTP = HTTP::Tiny->new(agent => 'Hildebrand-Lab-site-updater', timeout => 25, verify_SSL => 1);

sub today { return strftime('%Y-%m-%d', localtime) }

sub commify {
    my $digits = reverse shift;
    $digits =~ s/(\d{3})(?=\d)/$1,/g;
    return scalar reverse $digits;
}

sub is_count { my ($value) = @_; return defined $value && !ref $value && $value =~ /\A\d+\z/ }

sub read_json {
    my ($url) = @_;
    my %headers = (Accept => 'application/vnd.github+json');
    if ($ENV{GITHUB_TOKEN} && index($url, 'https://api.github.com/') == 0) {
        $headers{Authorization} = "Bearer $ENV{GITHUB_TOKEN}";
    }
    my $response = $HTTP->get($url, { headers => \%headers });
    unless ($response->{success}) {
        my $detail = $response->{status} == 599 ? $response->{content} : "HTTP $response->{status} $response->{reason}";
        chomp $detail;
        die "$detail\n";
    }
    return (decode_json($response->{content}), $response->{headers});
}

sub has_next_page {
    my ($payload, $headers) = @_;
    return @$payload == 100 && ($headers->{link} // '') =~ /rel="next"/;
}

sub bioconda_downloads {
    my ($package) = @_;
    my ($payload) = read_json("https://api.anaconda.org/package/$package");
    my $total = ref $payload eq 'HASH' ? $payload->{ndownloads} : undef;
    die "No download total returned for $package\n" unless is_count($total);
    return $total;
}

sub cran_downloads {
    my ($package) = @_;
    my $end = today();
    my ($payload) = read_json("https://cranlogs.r-pkg.org/downloads/total/$CRANLOGS_START:$end/$package");
    die "No CRAN download total returned for $package\n" unless ref $payload eq 'ARRAY' && @$payload;
    my $total = $payload->[0]{downloads};
    die "Invalid CRAN download total returned for $package\n" unless is_count($total);
    return $total;
}

sub github_release_downloads {
    my ($repository) = @_;
    # GitHub counts release assets only; it does not provide clone or source-archive totals.
    my $total = 0;
    for (my $page = 1; ; $page++) {
        my ($payload, $headers) = read_json("https://api.github.com/repos/$repository/releases?per_page=100&page=$page");
        die "Unexpected GitHub release response for $repository\n" unless ref $payload eq 'ARRAY';
        $total += sum0(map { $_->{download_count} // 0 } map { @{ $_->{assets} // [] } } @$payload);
        return $total unless has_next_page($payload, $headers);
    }
}

sub github_stars {
    my ($repository) = @_;
    my ($payload) = read_json("https://api.github.com/repos/$repository");
    die "Unexpected GitHub repository response for $repository\n" unless ref $payload eq 'HASH';
    my $total = $payload->{stargazers_count};
    die "No GitHub star count returned for $repository\n" unless is_count($total);
    return $total;
}

sub github_tag_count {
    my ($repository) = @_;
    my $total = 0;
    for (my $page = 1; ; $page++) {
        my ($payload, $headers) = read_json("https://api.github.com/repos/$repository/tags?per_page=100&page=$page");
        die "Unexpected GitHub tag response for $repository\n" unless ref $payload eq 'ARRAY';
        $total += @$payload;
        return $total unless has_next_page($payload, $headers);
    }
}

sub fetch_total {
    my ($source, $reference) = @_;
    return bioconda_downloads($reference)       if $source eq 'bioconda';
    return cran_downloads($reference)           if $source eq 'cran';
    return github_release_downloads($reference) if $source eq 'github';
    die "Unknown download source: $source\n";
}

# The hero summary is derived from the per-tool counters on the page, so it stays
# consistent with the cards even when an individual counter could not be refreshed.
sub update_summary {
    my ($html_ref, $failures) = @_;
    my %totals = (
        projects  => scalar(() = $$html_ref =~ /<article class="tool-detail-card">/g),
        downloads => sum0(map { tr/,//dr } $$html_ref =~ /data-download-stat="[^"]+">([\d,]+)</g),
        stars     => sum0(map { tr/,//dr } $$html_ref =~ /data-github-stars="[^"]+">([\d,]+)</g),
    );
    for my $key (sort keys %totals) {
        my $value = commify($totals{$key});
        $$html_ref =~ s{(<b data-software-summary="$key">)[\d,]+(</b>)}{$1$value$2}
            or push @$failures, "$key summary: statistic marker not found";
    }
    return \%totals;
}

sub main {
    open my $in, '<:raw', $PAGE or die "Cannot read $PAGE: $!\n";
    my $html = do { local $/; <$in> };
    close $in;
    my $original = $html;
    my %updated = (downloads => 0, stars => 0, versions => 0);
    my @failures;

    for my $name (sort keys %SOURCES) {
        my ($source, $reference) = @{ $SOURCES{$name} };
        my $total = eval { fetch_total($source, $reference) };
        unless (defined $total) {
            chomp(my $error = $@);
            push @failures, "$name downloads: $error";
            next;
        }
        my $class = $total >= 5 ? 'tool-stat' : 'tool-stat tool-stat-low';
        my $replacement = qq{<p class="$class"><span data-download-stat="$name">} . commify($total) . qq{</span> $DOWNLOAD_LABELS{$source}</p>};
        if ($html =~ s{<p class="tool-stat(?: tool-stat-low)?"><span data-download-stat="\Q$name\E">[\d,]+</span> [^<]+</p>}{$replacement}) {
            $updated{downloads}++;
        } else {
            push @failures, "$name downloads: statistic marker not found";
        }
    }

    for my $name (sort keys %REPOSITORIES) {
        my $total = eval { github_stars($REPOSITORIES{$name}) };
        unless (defined $total) {
            chomp(my $error = $@);
            push @failures, "$name stars: $error";
            next;
        }
        my $label = $total == 1 ? 'GitHub star' : 'GitHub stars';
        my $replacement = qq{<b data-github-stars="$name">} . commify($total) . "</b> $label";
        if ($html =~ s{<b data-github-stars="\Q$name\E">[\d,]+</b> GitHub stars?}{$replacement}) {
            $updated{stars}++;
        } else {
            push @failures, "$name stars: statistic marker not found";
        }
    }

    for my $name (sort keys %TAGGED_VERSION_REPOSITORIES) {
        my $total = eval { github_tag_count($TAGGED_VERSION_REPOSITORIES{$name}) };
        unless (defined $total) {
            chomp(my $error = $@);
            push @failures, "$name tagged versions: $error";
            next;
        }
        my $label = $total == 1 ? 'tagged version' : 'tagged versions';
        my $replacement = qq{<b data-github-versions="$name">} . commify($total) . "</b> $label";
        if ($html =~ s{<b data-github-versions="\Q$name\E">[\d,]+</b> tagged versions?}{$replacement}) {
            $updated{versions}++;
        } else {
            push @failures, "$name tagged versions: statistic marker not found";
        }
    }

    my $summary = update_summary(\$html, \@failures);

    if ($html ne $original) {
        open my $out, '>:raw', $PAGE or die "Cannot write $PAGE: $!\n";
        print {$out} $html;
        close $out or die "Cannot write $PAGE: $!\n";
    }
    printf "Updated %d download counters, %d GitHub star counters, and %d tagged-version counters on %s.\n",
        @updated{qw(downloads stars versions)}, today();
    printf "Summary: %s tools and resources, %s downloads, %s GitHub stars.\n",
        map { commify($summary->{$_}) } qw(projects downloads stars);
    print STDERR 'Could not update: ' . join('; ', sort @failures) . "\n" if @failures;
    return $updated{downloads} || $updated{stars} || $updated{versions} ? 0 : 1;
}

exit main();
