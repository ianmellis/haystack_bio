from __future__ import division
import os
import sys
import glob
import shutil
import argparse
import multiprocessing

import subprocess as sb

from haystack_common import check_file, HAYSTACK_VERSION

import logging
logging.basicConfig(level=logging.INFO,
                    format='%(levelname)-5s @ %(asctime)s:\n\t %(message)s \n',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    stream=sys.stderr,
                    filemode="w"
                    )
error = logging.critical
warn = logging.warning
debug = logging.debug
info = logging.info

#from memory_profiler import profile
#f = open('pipeline_memory.txt', 'w+')


def get_args_pipeline():
    # mandatory
    parser = argparse.ArgumentParser(description='HAYSTACK Parameters')
    parser.add_argument('samples_filename_or_bam_folder', type=str,
                        help='A tab delimeted file with in each row (1) a sample name, (2) the path to the corresponding bam filename, (3 optional) the path to the corresponding gene expression filename.')
    parser.add_argument('genome_name', type=str, help='Genome assembly to use from UCSC (for example hg19, mm9, etc.)')

    # optional
    parser.add_argument('--name', help='Define a custom output filename for the report', default='')
    parser.add_argument('--output_directory', type=str, help='Output directory (default: current directory)',
                        default='')
    parser.add_argument('--bin_size', type=int, help='bin size to use(default: 500bp)', default=500)
    parser.add_argument('--do_not_recompute',
                        help='Keep any file previously precalculated',
                        action='store_true')
    parser.add_argument('--do_not_filter_bams',
                        help='Use BAM files as provided. Do not remove reads that are unmapped, mate unmapped,'
                             ' not primary aligned or low MAPQ reads, reads failing qc and optical duplicates',
                        action='store_true')
    parser.add_argument('--depleted',
                        help='Look for cell type specific regions with depletion of signal instead of enrichment',
                        action='store_true')
    parser.add_argument('--input_is_bigwig',
                        help='Use the bigwig format instead of the bam format for the input. Note: The files must have extension .bw',
                        action='store_true')
    parser.add_argument('--disable_quantile_normalization', help='Disable quantile normalization (default: False)',
                        action='store_true')
    parser.add_argument('--transformation', type=str,
                        help='Variance stabilizing transformation among: none, log2, angle (default: angle)',
                        default='angle', choices=['angle', 'log2', 'none'])
    parser.add_argument('--z_score_high', type=float, help='z-score value to select the specific regions(default: 1.5)',
                        default=1.5)
    parser.add_argument('--z_score_low', type=float,
                        help='z-score value to select the not specific regions(default: 0.25)', default=0.25)
    parser.add_argument('--th_rpm', type=float,
                        help='Percentile on the signal intensity to consider for the hotspots (default: 99)',
                        default=99)
    parser.add_argument('--meme_motifs_filename', type=str,
                        help='Motifs database in MEME format (default JASPAR CORE 2016)')
    parser.add_argument('--motif_mapping_filename', type=str,
                        help='Custom motif to gene mapping file (the default is for JASPAR CORE 2016 database)')
    parser.add_argument('--plot_all',
                        help='Disable the filter on the TF activity and correlation (default z-score TF>0 and rho>0.3)',
                        action='store_true')
    parser.add_argument('--keep_intermediate_files',
                        help='keep intermediate bedgraph files ',
                        action='store_true')
    parser.add_argument('--n_processes', type=int,
                        help='Specify the number of processes to use. The default is #cores available.',
                        default=min(4, multiprocessing.cpu_count()))
    parser.add_argument('--blacklist',
                        type=str,
                        help='Exclude blacklisted regions. Blacklisted regions are not excluded by default. '
                             'Use hg19 to blacklist regions for the human genome 19, '
                             'otherwise provide the filepath for a bed file with blacklisted regions.',
                        default='none')
    parser.add_argument('--chrom_exclude',
                        type=str,
                        help='Exclude chromosomes that contain given (regex) string. For example _random|chrX|chrY excludes  random, X, and Y chromosome regions',
                        default='_|chrX|chrY')
    parser.add_argument('--read_ext', type=int, help='Read extension in bps (default: 200)', default=200)
    parser.add_argument('--temp_directory', help='Directory to store temporary files  (default: /tmp)', default='/tmp')
    parser.add_argument('--rho_cutoff',
                        type=float,
                        default=0.3,
                        help='The cutoff absolute correlation value (0.0 to 1)  for which activity plots are generated (default: 0.3)')
    parser.add_argument('--tf_value_cuttoff',
                        type=float,
                        default=0.0,
                        help='The cutoff z-score tf_value for which activity plots are generated (default: 0.0) ')
    parser.add_argument('--version', help='Print version and exit.', action='version',
                        version='Version %s' % HAYSTACK_VERSION)

    return parser

#@profile
def main(input_args=None):

    print '\n[H A Y S T A C K   P I P E L I N E]'
    print('\n-SELECTION OF HOTSPOTS OF VARIABILITY AND ENRICHED MOTIFS-\n')
    print 'Version %s\n' % HAYSTACK_VERSION
    parser = get_args_pipeline()
    args = parser.parse_args(input_args)

    args_dict = vars(args)
    for key, value in args_dict.items():
        exec ('%s=%s' % (key, repr(value)))

    if meme_motifs_filename:
        check_file(meme_motifs_filename)

    if motif_mapping_filename:
        check_file(motif_mapping_filename)

    if not os.path.exists(temp_directory):
        error('The folder specified with --temp_directory: %s does not exist!' % temp_directory)
        sys.exit(1)

    if input_is_bigwig:
        extension_to_check = '.bw'
        info('Input is set BigWig (.bw)')
    else:
        extension_to_check = '.bam'
        info('Input is set compressed SAM (.bam)')

    if name:
        directory_name = 'HAYSTACK_PIPELINE_RESULTS_on_%s' % name

    else:
        directory_name = 'HAYSTACK_PIPELINE_RESULTS'

    if output_directory:
        output_directory = os.path.join(output_directory, directory_name)
    else:
        output_directory = directory_name

    # check folder or sample filename

    USE_GENE_EXPRESSION = True
    if not os.path.exists(samples_filename_or_bam_folder):
        error("The file or folder %s doesn't exist. Exiting." %
              samples_filename_or_bam_folder)
        sys.exit(1)

    if os.path.isfile(samples_filename_or_bam_folder):
        BAM_FOLDER = False
        data_filenames = []
        gene_expression_filenames = []
        sample_names = []

        with open(samples_filename_or_bam_folder) as infile:
            for line in infile:

                if not line.strip():
                    continue

                if line.startswith('#'):  # skip optional header line or empty lines
                    info('Skipping header/comment line:%s' % line)
                    continue

                fields = line.strip().split()
                n_fields = len(fields)

                if n_fields == 2:

                    USE_GENE_EXPRESSION = False

                    sample_names.append(fields[0])
                    data_filenames.append(fields[1])

                elif n_fields == 3:

                    USE_GENE_EXPRESSION = USE_GENE_EXPRESSION and True
                    sample_names.append(fields[0])
                    data_filenames.append(fields[1])
                    gene_expression_filenames.append(fields[2])
                else:
                    error('The samples file format is wrong!')
                    sys.exit(1)
    else:
        if os.path.exists(samples_filename_or_bam_folder):
            BAM_FOLDER = True
            USE_GENE_EXPRESSION = False
            data_filenames = glob.glob(os.path.join(samples_filename_or_bam_folder, '*' + extension_to_check))

            if not data_filenames:
                error('No bam/bigwig  files to analyze in %s. Exiting.' % samples_filename_or_bam_folder)
                sys.exit(1)

            sample_names = [os.path.basename(data_filename).replace(extension_to_check, '') for data_filename in
                            data_filenames]
        else:
            error("The file or folder %s doesn't exist. Exiting." % samples_filename_or_bam_folder)
            sys.exit(1)

    # check all the files before starting
    info('Checking samples files location...')
    for data_filename in data_filenames:
        check_file(data_filename)

    if USE_GENE_EXPRESSION:
        for gene_expression_filename in gene_expression_filenames:
            check_file(gene_expression_filename)

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # copy back the file used
    if not BAM_FOLDER:
        shutil.copy2(samples_filename_or_bam_folder, output_directory)

    # write hotspots conf files
    sample_names_hotspots_filename = os.path.join(output_directory,
                                                  'sample_names_hotspots.txt')

    with open(sample_names_hotspots_filename, 'w+') as outfile:
        for sample_name, data_filename in zip(sample_names, data_filenames):
            outfile.write('%s\t%s\n' % (sample_name, data_filename))


    #CALL HAYSTACK HOTSPOTS
    cmd_to_run='haystack_hotspots %s %s --output_directory %s --bin_size %d %s %s %s %s %s %s %s %s %s %s %s %s %s %s' % \
                (sample_names_hotspots_filename, genome_name,output_directory,bin_size,
                 ('--do_not_filter_bams' if do_not_filter_bams else ''),
                 ('--depleted' if depleted else ''),
                 ('--do_not_recompute' if do_not_recompute else ''),
                 ('--keep_intermediate_files' if keep_intermediate_files else ''),
                 ('--input_is_bigwig' if input_is_bigwig else ''),
                 ('--disable_quantile_normalization' if disable_quantile_normalization else ''),
                 '--transformation %s' % transformation,
                 '--chrom_exclude "%s"' % chrom_exclude,
                 '--z_score_high %f' % z_score_high,
                 '--z_score_low %f' % z_score_low,
                 '--th_rpm %f' % th_rpm,
                 '--blacklist %s' % blacklist,
                 '--read_ext %d' % read_ext,
                 '--n_processes %d' % n_processes)
    print(cmd_to_run)
    sb.call(cmd_to_run ,shell=True)


    # CALL HAYSTACK MOTIFS
    motif_directory = os.path.join(output_directory,'HAYSTACK_MOTIFS')


    for sample_name in sample_names:
        specific_regions_filename = os.path.join(output_directory, 'HAYSTACK_HOTSPOTS', 'SPECIFIC_REGIONS',
                                                 'Regions_specific_for_%s*.bed' % sample_name)
        bg_regions_filename = glob.glob(os.path.join(output_directory, 'HAYSTACK_HOTSPOTS', 'SPECIFIC_REGIONS',
                                                     'Background_for_%s*.bed' % sample_name))[0]
        cmd_to_run = 'haystack_motifs %s %s --bed_bg_filename %s --output_directory %s --name %s' % (
        specific_regions_filename, genome_name, bg_regions_filename, motif_directory, sample_name)

        if meme_motifs_filename:
            cmd_to_run += ' --meme_motifs_filename %s' % meme_motifs_filename

        if n_processes:
            cmd_to_run += ' --n_processes %d' % n_processes

        if temp_directory:
            cmd_to_run += ' --temp_directory %s' % temp_directory

        print(cmd_to_run)
        sb.call(cmd_to_run, shell=True)


    if USE_GENE_EXPRESSION:

        sample_names_tf_activity_filename = os.path.join(output_directory,
                                                         'sample_names_tf_activity.txt')

        with open(sample_names_tf_activity_filename, 'w+') as outfile:
            for sample_name, gene_expression_filename in zip(sample_names,
                                                             gene_expression_filenames):
                outfile.write('%s\t%s\n' % (sample_name,
                                            gene_expression_filename))

        tf_activity_directory = os.path.join(output_directory,
                                             'HAYSTACK_TFs_ACTIVITY_PLANES')

        for sample_name in sample_names:

            # write tf activity  conf files


            # CALL HAYSTACK TF ACTIVITY
            motifs_output_folder = os.path.join(motif_directory,
                                                'HAYSTACK_MOTIFS_on_%s' % sample_name)

            if os.path.exists(motifs_output_folder):
                cmd_to_run='haystack_tf_activity_plane %s %s %s --output_directory %s'  %(motifs_output_folder,
                                                                                          sample_names_tf_activity_filename,
                                                                                          sample_name,
                                                                                          tf_activity_directory)

            if motif_mapping_filename:
                cmd_to_run+=' --motif_mapping_filename %s' %  motif_mapping_filename

            if plot_all:
                cmd_to_run+=' --plot_all'

            if rho_cutoff:
                cmd_to_run += ' --rho_cutoff %f' % rho_cutoff

            if tf_value_cuttoff:
                cmd_to_run += ' --tf_value_cuttoff %f' % tf_value_cuttoff

            print(cmd_to_run)
            sb.call(cmd_to_run, shell=True)


if __name__ == '__main__':
    main()
