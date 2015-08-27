#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import argparse
import os
from subprocess import Popen, PIPE
from os import environ
from os.path import abspath, dirname, join
import sys
import shutil
from lib import source, backup_build_models, load_dict, build_dict, extract_alphabet, extract_vocabulary


if __name__ == '__main__':
    try:
        exit_on_system_fail("lattice-oracle --help")
    except RuntimeError:
        print >> sys.stderr, "Kaldi binaries not available"
        exit_on_system_fail("echo $PATH")
        exit 1

    parser = argparse.ArgumentParser(description='Build HCLG graph for Kaldi')
    parser.add_argument('--path-sh', help='shell script updating PATH to include IRSTLM and Kaldi binaries', default='/kaldi_uproot/kams/kams/path.sh')
    parser.add_argument('--lm', help='LM in arpa format', required=True)
    parser.add_argument('-oov', '--out-of-vocabulary', default='<UNK>')
    parser.add_argument('-tmp', '--tmp-directory', default=join(abspath(dirname(__file__), 'tmp')))
    parser.add_argument('--out-dir', default=join(abspath(dirname(__file__), 'out_dir')))
    # FIXME timestamp

    # TODO supporting only tri2b
    am_group = parser.add_argument_group('AM training files')
    am_group.add_argument('--am', help='Acoustic model - typically you want final.mdl from Kaldi training scripts.', required=True)
    am_group.add_argument('--conf', help='Configuration file which should store all non-default values used for acoustic signal preprocessing and AM parameters which needs to be the same during decoding.', required=True)
    am_group.add_argument('--tree', help='Tree for tying GMM - Gaussian Mixture Models.', required=True)
    am_group.add_argument('--mat', help='Matrix for linear transformation e.g. lda+mllt.', required=True)
    am_group.add_argument('--sil', '--silence-phones-ids', required=True)  # TODO use them more


    subparses = parser.add_subparsers()
    load_dict_parser = subparser.add_parser('load_dict')
    load_dict_parser.add_argument('-f', help='Path to phonetic dictionary')
    load_dict_parser.set_defaults(prepare_lm_dict=load_dict)

    build_dict_parser = subparser.add_parser('build_dict')
    build_dict_parser.add_argument('--lang', choices=['cs', 'en'])
    build_dict_parser.set_defaults(prepare_lm_dict=build_dict)

    args = parser.parse_args()

    lm_dict = args.prepare_lm_dict(args)
    am_dict = load_dict(args.am_dict)
    phonetic_alphabet_lm = extract_alphabet(lm_dict)
    phonetic_alphabet_am = extract_alphabet(am_dict)

    # Check phonetic alphabets are exactly the same
    assert len(phonetic_alphabet_am) == len(phonetic_alphabet_lm) and len([x for x in phonetic_alphabet_am if x not in phonetic_alphabet_lm]) == 0

    common_keys = set(lm_dict.keys()) & set(am_dict.keys())
    diff_pronunciation = [am_dict[c], lm_dict[c] for c in common_keys if am_dict[c] != lm_dict[c]]
    if len(diff_pronunciation) == 0:
        print >> sys.stderr, "Phonetic dictionaries are the same"
    for a, b in diff_pronunciation:
        print >> sys.stderr, "Phonetic dictionary differs:  %s vs %s" % (a, b)


    env = source(args.path_sh)

    with open('%(tmpdir)s/vocabulary', 'w') as w:
        w.write('\n'.join(sorted(extract_vocabulary(lm_dict))))

    exit_on_system_fail("./prepare_kaldi_lang_files.sh %(model)s %(tree)s %(conf)s %(mat)s %(sil)s %(dictionary)s %(vocabulary)s %(lm_arpa)s %(oov)s %(tmpdir)s %(out_dir)s" % vars(args))


    cp $model $locdata/final.mdl  # $locdata mus contain AM and phonetic DT
    cp $tree $locdata/tree  # $locdata mus contain AM and phonetic DT
    cp matrix
    conf=$1; shift
    sil=$1; shift

    # exit_on_system_fail("source path.sh; utils/mkgraph.sh $lang $locdata $hclg"
    # utils/mkgraph.sh $lang $locdata $hclg || exit 1 # FIXME delete
    exit_on_system_fail("source path.sh; utils/mkgraph.sh %(tmp)s/lang %(tmp) %s(tmp)/hclg" % vars(args))
    # FIXME
    # to make const fst:
    # fstconvert --fst_type=const $dir/HCLG.fst $dir/HCLG_c.fst

    backup_build_models(vars(args))